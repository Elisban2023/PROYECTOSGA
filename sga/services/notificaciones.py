"""Servicios de notificaciones internas y envio por correo."""

from django.conf import settings
from django.utils import timezone

from sga.models import EstadoEnvio
from sga.roles import ROLE_APODERADO
from sga.services.correos import CorreoError, enviar_por_sendgrid, renderizar_correo


def enviar_notificacion(notificacion):
    """Envia una notificacion por correo si SendGrid esta habilitado."""
    if not settings.SENDGRID_ENABLED:
        return notificacion

    try:
        _enviar_correo_sendgrid(notificacion)
    except CorreoError:
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
    destinatario = notificacion.apoderado.perfil.user
    accion_url = f"{settings.FRONTEND_URL}/apoderado/notificaciones"
    contenido = renderizar_correo(
        destinatario=destinatario,
        rol=ROLE_APODERADO,
        asunto=notificacion.titulo,
        mensaje=notificacion.mensaje,
        accion_texto="Ver notificacion",
        accion_url=accion_url,
    )
    enviar_por_sendgrid(
        destinatario=destinatario,
        asunto=notificacion.titulo,
        texto=contenido["texto"],
        html=contenido["html"],
    )
