"""Servicios de notificaciones internas y envio por correo."""

import json
from urllib import error, request

from django.conf import settings
from django.utils import timezone

from sga.models import EstadoEnvio

SENDGRID_MAIL_SEND_URL = "https://api.sendgrid.com/v3/mail/send"


class NotificacionError(Exception):
    pass


def enviar_notificacion(notificacion):
    """Envia una notificacion por correo si SendGrid esta habilitado."""
    if not settings.SENDGRID_ENABLED:
        return notificacion

    try:
        _enviar_correo_sendgrid(notificacion)
    except NotificacionError:
        notificacion.estado_envio = EstadoEnvio.FALLIDA
        notificacion.fecha_envio = timezone.now()
        notificacion.save(update_fields=["estado_envio", "fecha_envio"])
        return notificacion

    notificacion.estado_envio = EstadoEnvio.ENVIADA
    notificacion.fecha_envio = timezone.now()
    notificacion.save(update_fields=["estado_envio", "fecha_envio"])
    return notificacion


def marcar_como_leida(notificacion):
    notificacion.estado_envio = EstadoEnvio.LEIDA
    notificacion.fecha_lectura = timezone.now()
    notificacion.save(update_fields=["estado_envio", "fecha_lectura"])
    return notificacion


def _enviar_correo_sendgrid(notificacion):
    api_key = settings.SENDGRID_API_KEY
    from_email = settings.SENDGRID_FROM_EMAIL
    from_name = settings.SENDGRID_FROM_NAME
    to_email = notificacion.apoderado.perfil.user.email
    to_name = notificacion.apoderado.perfil.user.get_full_name() or notificacion.apoderado.perfil.user.username

    if not api_key:
        raise NotificacionError("SENDGRID_API_KEY no configurado.")
    if not from_email:
        raise NotificacionError("SENDGRID_FROM_EMAIL no configurado.")
    if not to_email:
        raise NotificacionError("El apoderado no tiene correo electronico.")

    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email, "name": to_name}],
                "subject": notificacion.titulo,
            }
        ],
        "from": {"email": from_email, "name": from_name},
        "content": [
            {
                "type": "text/plain",
                "value": notificacion.mensaje,
            }
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    sendgrid_request = request.Request(
        SENDGRID_MAIL_SEND_URL,
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(sendgrid_request, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise NotificacionError(f"SendGrid respondio con estado {response.status}.")
    except error.HTTPError as exc:
        raise NotificacionError(f"SendGrid rechazo el envio: {exc.code}.") from exc
    except error.URLError as exc:
        raise NotificacionError("No se pudo conectar con SendGrid.") from exc
    except TimeoutError as exc:
        raise NotificacionError("Tiempo de espera agotado al enviar por SendGrid.") from exc
