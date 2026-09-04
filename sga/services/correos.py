"""Renderizado y envio de correos institucionales por SendGrid."""

import json
from urllib import error, request

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from sga.models import CorreoInstitucional, EstadoCorreo
from sga.roles import (
    ROLE_ADMIN,
    ROLE_APODERADO,
    ROLE_DIRECTIVO,
    ROLE_DOCENTE,
    ROLE_ESTUDIANTE,
)

SENDGRID_MAIL_SEND_URL = "https://api.sendgrid.com/v3/mail/send"

FORMATOS_ROL = {
    ROLE_ADMIN: {
        "plantilla": "administrador",
        "encabezado": "Gestion institucional",
        "descripcion": "Informacion administrativa del SGA",
        "color": "#334155",
    },
    ROLE_DIRECTIVO: {
        "plantilla": "administrador",
        "encabezado": "Gestion directiva",
        "descripcion": "Informacion institucional y academica",
        "color": "#334155",
    },
    ROLE_DOCENTE: {
        "plantilla": "docente",
        "encabezado": "Actividad docente",
        "descripcion": "Informacion de cursos y seguimiento academico",
        "color": "#2563eb",
    },
    ROLE_ESTUDIANTE: {
        "plantilla": "estudiante",
        "encabezado": "Informacion academica",
        "descripcion": "Novedades sobre tu aprendizaje",
        "color": "#047857",
    },
    ROLE_APODERADO: {
        "plantilla": "apoderado",
        "encabezado": "Seguimiento del estudiante",
        "descripcion": "Informacion para madres, padres y apoderados",
        "color": "#b45309",
    },
}


class CorreoError(Exception):
    """Error controlado de configuracion o comunicacion con SendGrid."""

    def __init__(self, mensaje, *, correo=None):
        super().__init__(mensaje)
        self.correo = correo


def renderizar_correo(*, destinatario, rol, asunto, mensaje, accion_texto=None, accion_url=None):
    formato = FORMATOS_ROL.get(rol)
    if formato is None:
        raise CorreoError("El rol del destinatario no tiene un formato de correo configurado.")

    contexto = {
        "nombre_destinatario": destinatario.get_full_name().strip() or destinatario.username,
        "rol": rol,
        "asunto": asunto,
        "mensaje": mensaje,
        "accion_texto": accion_texto,
        "accion_url": accion_url,
        "anio": timezone.localdate().year,
        **formato,
    }
    html = render_to_string(f"emails/{formato['plantilla']}.html", contexto)
    texto = render_to_string("emails/correo.txt", contexto)
    return {"html": html, "texto": texto, "formato": formato}


def enviar_por_sendgrid(*, destinatario, asunto, texto, html):
    if not settings.SENDGRID_ENABLED:
        raise CorreoError("El servicio de correo no esta habilitado.")
    if not settings.SENDGRID_API_KEY:
        raise CorreoError("La clave de SendGrid no esta configurada.")
    if not settings.SENDGRID_FROM_EMAIL:
        raise CorreoError("El remitente de SendGrid no esta configurado.")
    if not destinatario.email:
        raise CorreoError("El destinatario no tiene correo electronico.")

    nombre = destinatario.get_full_name().strip() or destinatario.username
    payload = {
        "personalizations": [{"to": [{"email": destinatario.email, "name": nombre}], "subject": asunto}],
        "from": {"email": settings.SENDGRID_FROM_EMAIL, "name": settings.SENDGRID_FROM_NAME},
        "content": [
            {"type": "text/plain", "value": texto},
            {"type": "text/html", "value": html},
        ],
    }
    solicitud = request.Request(
        SENDGRID_MAIL_SEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(solicitud, timeout=settings.SENDGRID_TIMEOUT) as respuesta:
            if not 200 <= respuesta.status < 300:
                raise CorreoError(f"SendGrid respondio con estado {respuesta.status}.")
    except error.HTTPError as exc:
        raise CorreoError(f"SendGrid rechazo el envio con estado {exc.code}.") from exc
    except error.URLError as exc:
        raise CorreoError("No se pudo conectar con SendGrid.") from exc
    except TimeoutError as exc:
        raise CorreoError("Se agoto el tiempo de espera al enviar el correo.") from exc


def enviar_correo_institucional(
    *,
    destinatario,
    enviado_por,
    rol,
    asunto,
    mensaje,
    accion_texto=None,
    accion_url=None,
    tipo="INSTITUCIONAL",
    matricula=None,
    asignacion_curso=None,
    periodo_academico=None,
    recomendacion=None,
    incidencia=None,
):
    correo = CorreoInstitucional.objects.create(
        destinatario=destinatario,
        enviado_por=enviado_por,
        rol_destinatario=rol,
        tipo=tipo,
        matricula=matricula,
        asignacion_curso=asignacion_curso,
        periodo_academico=periodo_academico,
        recomendacion=recomendacion,
        incidencia=incidencia,
        asunto=asunto,
        mensaje=mensaje,
        accion_texto=accion_texto,
        accion_url=accion_url,
    )
    try:
        contenido = renderizar_correo(
            destinatario=destinatario,
            rol=rol,
            asunto=asunto,
            mensaje=mensaje,
            accion_texto=accion_texto,
            accion_url=accion_url,
        )
        enviar_por_sendgrid(
            destinatario=destinatario,
            asunto=asunto,
            texto=contenido["texto"],
            html=contenido["html"],
        )
    except CorreoError as exc:
        correo.estado = EstadoCorreo.FALLIDO
        correo.detalle_error = str(exc)[:250]
        correo.save(update_fields=["estado", "detalle_error"])
        raise CorreoError(str(exc), correo=correo) from exc

    correo.estado = EstadoCorreo.ENVIADO
    correo.fecha_envio = timezone.now()
    correo.detalle_error = None
    correo.save(update_fields=["estado", "fecha_envio", "detalle_error"])
    return correo
