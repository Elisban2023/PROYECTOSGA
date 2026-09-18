import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from sga.models import DesafioMFA, EventoAutenticacion, TipoEventoAutenticacion
from sga.roles import get_primary_role, is_admin_or_directivo
from sga.services.correos import CorreoError, enviar_por_sendgrid, renderizar_correo

User = get_user_model()


def obtener_ip(request):
    return request.META.get("REMOTE_ADDR") or None


def registrar_evento_autenticacion(request, tipo, *, user=None, exitoso=False, identificador=None, detalle=None):
    identificador_hash = None
    if identificador:
        identificador_hash = salted_hmac(
            "sga.evento-autenticacion",
            identificador.strip().lower(),
            secret=settings.SECRET_KEY,
            algorithm="sha256",
        ).hexdigest()
    return EventoAutenticacion.objects.create(
        user=user,
        tipo=tipo,
        exitoso=exitoso,
        identificador_hash=identificador_hash,
        direccion_ip=obtener_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255] or None,
        detalle=(detalle or "")[:150] or None,
    )


def emitir_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "session": configuracion_sesion(),
    }


def configuracion_sesion():
    return {
        "idle_timeout_seconds": settings.SESSION_IDLE_TIMEOUT_MINUTES * 60,
        "access_expires_in_seconds": int(
            settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
        ),
        "refresh_rotation": bool(settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS")),
    }


def iniciar_desafio_mfa(user, request):
    if not user.email:
        raise CorreoError("La cuenta administrativa no tiene un correo configurado para MFA.")

    ahora = timezone.now()
    DesafioMFA.objects.filter(user=user, usado=False).update(usado=True)
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    desafio = DesafioMFA.objects.create(
        user=user,
        codigo_hash=make_password(codigo),
        expira_en=ahora + timedelta(minutes=settings.MFA_CODE_TTL_MINUTES),
    )
    rol = get_primary_role(user)
    contenido = renderizar_correo(
        destinatario=user,
        rol=rol,
        asunto="Codigo de verificacion para iniciar sesion",
        mensaje=(
            f"Tu codigo de verificacion es: {codigo}\n\n"
            f"Caduca en {settings.MFA_CODE_TTL_MINUTES} minutos. "
            "Si no intentaste iniciar sesion, cambia tu contrasena y comunicate con el responsable del sistema."
        ),
    )
    try:
        enviar_por_sendgrid(
            destinatario=user,
            asunto="Codigo de verificacion para iniciar sesion",
            texto=contenido["texto"],
            html=contenido["html"],
        )
    except CorreoError:
        desafio.usado = True
        desafio.save(update_fields=["usado"])
        raise

    registrar_evento_autenticacion(
        request,
        TipoEventoAutenticacion.MFA_SOLICITADO,
        user=user,
        exitoso=True,
    )
    return desafio


@transaction.atomic
def verificar_desafio_mfa(desafio_id, codigo, request):
    desafio = DesafioMFA.objects.select_for_update().select_related("user").filter(pk=desafio_id).first()
    if desafio is None or desafio.usado or desafio.expira_en <= timezone.now():
        return None, "El codigo es invalido o ha expirado."
    if desafio.intentos >= settings.MFA_MAX_ATTEMPTS:
        desafio.usado = True
        desafio.save(update_fields=["usado"])
        return None, "El codigo es invalido o ha expirado."

    if not check_password(codigo, desafio.codigo_hash):
        desafio.intentos += 1
        if desafio.intentos >= settings.MFA_MAX_ATTEMPTS:
            desafio.usado = True
        desafio.save(update_fields=["intentos", "usado"])
        registrar_evento_autenticacion(
            request,
            TipoEventoAutenticacion.MFA_FALLIDO,
            user=desafio.user,
            detalle="Codigo incorrecto",
        )
        return None, "El codigo es invalido o ha expirado."

    if not desafio.user.is_active or not is_admin_or_directivo(desafio.user):
        desafio.usado = True
        desafio.save(update_fields=["usado"])
        return None, "El codigo es invalido o ha expirado."

    desafio.usado = True
    desafio.save(update_fields=["usado"])
    registrar_evento_autenticacion(
        request,
        TipoEventoAutenticacion.MFA_EXITOSO,
        user=desafio.user,
        exitoso=True,
    )
    return desafio.user, None


def solicitar_recuperacion_password(email, request):
    user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
    registrar_evento_autenticacion(
        request,
        TipoEventoAutenticacion.PASSWORD_RESET_SOLICITADO,
        user=user,
        exitoso=user is not None,
        identificador=email,
    )
    if user is None or not user.email:
        return

    limite = timezone.now() - timedelta(seconds=settings.PASSWORD_RESET_RESEND_SECONDS)
    if EventoAutenticacion.objects.filter(
        user=user,
        tipo=TipoEventoAutenticacion.PASSWORD_RESET_ENVIADO,
        exitoso=True,
        fecha__gte=limite,
    ).exists():
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    enlace = f"{settings.FRONTEND_URL}{settings.PASSWORD_RESET_FRONTEND_PATH}?uid={uid}&token={token}"
    rol = get_primary_role(user)
    if rol is None:
        return
    contenido = renderizar_correo(
        destinatario=user,
        rol=rol,
        asunto="Recuperacion de contrasena",
        mensaje=(
            "Recibimos una solicitud para cambiar tu contrasena. "
            f"El enlace caduca en {settings.PASSWORD_RESET_TIMEOUT // 60} minutos. "
            "Si no realizaste esta solicitud, ignora este mensaje."
        ),
        accion_texto="Validar solicitud",
        accion_url=enlace,
    )
    try:
        enviar_por_sendgrid(
            destinatario=user,
            asunto="Recuperacion de contrasena",
            texto=contenido["texto"],
            html=contenido["html"],
        )
    except CorreoError:
        registrar_evento_autenticacion(
            request,
            TipoEventoAutenticacion.PASSWORD_RESET_ENVIADO,
            user=user,
            detalle="Fallo del proveedor de correo",
        )
        return
    registrar_evento_autenticacion(
        request,
        TipoEventoAutenticacion.PASSWORD_RESET_ENVIADO,
        user=user,
        exitoso=True,
    )


def usuario_desde_token(uid, token):
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        user = User.objects.filter(pk=user_id, is_active=True).first()
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
        return None
    if user is None or not default_token_generator.check_token(user, token):
        return None
    return user


@transaction.atomic
def cambiar_password_con_token(uid, token, nueva_password, request):
    try:
        user_id = urlsafe_base64_decode(uid).decode()
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
        return None
    user = User.objects.select_for_update().filter(pk=user_id, is_active=True).first()
    if user is None or not default_token_generator.check_token(user, token):
        return None
    user.set_password(nueva_password)
    user.save(update_fields=["password"])
    revocar_sesiones(user)
    DesafioMFA.objects.filter(user=user, usado=False).update(usado=True)
    registrar_evento_autenticacion(
        request,
        TipoEventoAutenticacion.PASSWORD_RESET_COMPLETADO,
        user=user,
        exitoso=True,
    )
    return user


def revocar_sesiones(user):
    for outstanding in OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now()):
        BlacklistedToken.objects.get_or_create(token=outstanding)
