"""Bandeja interna y entrega de notificaciones por correo."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from sga.models import (
    Apoderado,
    EstadoEnvio,
    EstadoGeneral,
    EstadoIncidencia,
    EstadoMatricula,
    IncidenciaAcademica,
    Matricula,
    Notificacion,
)
from sga.roles import (
    ROLE_ADMIN,
    ROLE_APODERADO,
    ROLE_DIRECTIVO,
    ROLE_DOCENTE,
    ROLE_ESTUDIANTE,
    get_primary_role,
)
from sga.services.correos import CorreoError, enviar_por_sendgrid, renderizar_correo
from sga.services.docente import get_asignaciones_docente


RUTAS_NOTIFICACIONES = {
    ROLE_ADMIN: "/notificaciones",
    ROLE_DIRECTIVO: "/notificaciones",
    ROLE_DOCENTE: "/docente/notificaciones",
    ROLE_ESTUDIANTE: "/estudiante/notificaciones",
    ROLE_APODERADO: "/apoderado/notificaciones",
}


def get_notificaciones_usuario(user):
    return (
        Notificacion.objects.filter(destinatario=user, activo=True)
        .select_related(
            "destinatario",
            "enviado_por_docente__perfil__user",
            "incidencia__matricula__estudiante__perfil__user",
            "recomendacion__matricula__estudiante__perfil__user",
            "apoderado__perfil__user",
        )
        .order_by("-id")
    )


def get_notificaciones_enviadas_docente(user):
    return (
        Notificacion.objects.filter(
            enviado_por_docente=user.perfil.docente,
            activo=True,
        )
        .select_related(
            "destinatario",
            "incidencia",
            "recomendacion__matricula__estudiante__perfil__user",
            "apoderado__perfil__user",
        )
        .order_by("-id")
    )


def get_destinatarios_docente(user, *, rol=None, buscar=None, incidencia_id=None):
    usuarios = _destinatarios_permitidos(user, incidencia_id=incidencia_id)
    if rol:
        if rol not in (ROLE_ADMIN, ROLE_DIRECTIVO, ROLE_DOCENTE, ROLE_ESTUDIANTE, ROLE_APODERADO):
            raise ValidationError({"rol": "El rol seleccionado no es valido."})
        if rol == ROLE_ADMIN:
            usuarios = usuarios.filter(Q(groups__name=ROLE_ADMIN) | Q(is_superuser=True))
        elif rol == ROLE_DIRECTIVO:
            usuarios = usuarios.filter(groups__name=ROLE_DIRECTIVO)
        else:
            usuarios = usuarios.filter(groups__name=rol)
    if buscar:
        buscar = buscar.strip()
        usuarios = usuarios.filter(
            Q(username__icontains=buscar)
            | Q(first_name__icontains=buscar)
            | Q(last_name__icontains=buscar)
            | Q(perfil__dni__icontains=buscar)
        )
    return usuarios.distinct().order_by("last_name", "first_name", "username")


def crear_notificaciones_docente(
    user,
    *,
    destinatarios,
    titulo,
    mensaje,
    tipo,
    prioridad,
    incidencia_id=None,
    accion_url=None,
    recomendacion=None,
    datos_extra=None,
):
    ids = list(dict.fromkeys(destinatarios))
    if len(ids) > 20:
        raise ValidationError({"destinatarios": "Puede enviar a un maximo de 20 destinatarios por operacion."})

    permitidos = get_destinatarios_docente(
        user,
        incidencia_id=incidencia_id,
    ).filter(id__in=ids)
    permitidos_por_id = {usuario.id: usuario for usuario in permitidos}
    no_permitidos = [usuario_id for usuario_id in ids if usuario_id not in permitidos_por_id]
    if no_permitidos:
        raise ValidationError(
            {"destinatarios": "Uno o mas destinatarios no pertenecen al alcance academico del docente."}
        )

    incidencia = None
    if incidencia_id:
        incidencia = _incidencia_docente(user, incidencia_id)

    creadas = []
    with transaction.atomic():
        for usuario_id in ids:
            destinatario = permitidos_por_id[usuario_id]
            rol = get_primary_role(destinatario)
            apoderado = None
            if rol == ROLE_APODERADO:
                apoderado = Apoderado.objects.filter(perfil__user=destinatario).first()
            notificacion = Notificacion.objects.create(
                incidencia=incidencia,
                recomendacion=recomendacion,
                apoderado=apoderado,
                destinatario=destinatario,
                enviado_por_docente=user.perfil.docente,
                tipo=tipo,
                prioridad=prioridad,
                titulo=titulo,
                mensaje=mensaje,
                accion_url=accion_url or RUTAS_NOTIFICACIONES.get(rol, "/notificaciones"),
                datos={**_datos_contexto(incidencia), **(datos_extra or {})},
                estado_envio=EstadoEnvio.PENDIENTE,
            )
            creadas.append(notificacion)

    for notificacion in creadas:
        enviar_notificacion(notificacion)
    return creadas


def enviar_notificacion(notificacion):
    """Conserva la notificacion interna incluso cuando falle el correo."""
    if not settings.SENDGRID_ENABLED:
        return _registrar_fallo(notificacion, "El servicio de correo no esta habilitado.")

    try:
        _enviar_correo_sendgrid(notificacion)
    except CorreoError as exc:
        return _registrar_fallo(notificacion, str(exc))

    notificacion.estado_envio = EstadoEnvio.ENVIADA
    notificacion.fecha_envio = timezone.now()
    notificacion.detalle_error = None
    notificacion.save(update_fields=["estado_envio", "fecha_envio", "detalle_error"])
    return notificacion


def marcar_como_leida(notificacion):
    if notificacion.fecha_lectura:
        return notificacion
    notificacion.fecha_lectura = timezone.now()
    notificacion.save(update_fields=["fecha_lectura"])
    return notificacion


def marcar_todas_como_leidas(user):
    return get_notificaciones_usuario(user).filter(fecha_lectura__isnull=True).update(
        fecha_lectura=timezone.now()
    )


def _destinatarios_permitidos(user, *, incidencia_id=None):
    User = get_user_model()
    asignaciones = get_asignaciones_docente(user).filter(estado=EstadoGeneral.ACTIVO)
    condicion_matriculas = Q(pk__in=[])
    for seccion_id, anio_id in asignaciones.values_list(
        "seccion_id", "anio_academico_id"
    ).distinct():
        condicion_matriculas |= Q(seccion_id=seccion_id, anio_academico_id=anio_id)
    matriculas = Matricula.objects.filter(condicion_matriculas, estado=EstadoMatricula.ACTIVA)

    if incidencia_id:
        incidencia = _incidencia_docente(user, incidencia_id)
        matriculas = matriculas.filter(pk=incidencia.matricula_id)

    estudiantes = Q(perfil__estudiante__matriculas__in=matriculas)
    apoderados = Q(
        perfil__apoderado__vinculos_estudiantes__estudiante_id__in=matriculas.values("estudiante_id")
    )
    pares = asignaciones.values_list("seccion_id", "anio_academico_id").distinct()
    docentes = Q(pk__in=[])
    for seccion_id, anio_id in pares:
        docentes |= Q(
            perfil__docente__asignaciones_curso__seccion_id=seccion_id,
            perfil__docente__asignaciones_curso__anio_academico_id=anio_id,
            perfil__docente__asignaciones_curso__estado=EstadoGeneral.ACTIVO,
        )
    administracion = Q(is_staff=True) | Q(is_superuser=True) | Q(
        groups__name__in=(ROLE_ADMIN, ROLE_DIRECTIVO)
    )
    return User.objects.filter(
        estudiantes | apoderados | docentes | administracion,
        is_active=True,
    ).exclude(pk=user.pk)


def _incidencia_docente(user, incidencia_id):
    incidencia = (
        IncidenciaAcademica.objects.filter(
            pk=incidencia_id,
            observacion__docente=user.perfil.docente,
            observacion__asignacion_curso__docente=user.perfil.docente,
        )
        .select_related("matricula__estudiante")
        .first()
    )
    if incidencia is None:
        raise ValidationError({"incidencia_id": "La incidencia no pertenece al docente autenticado."})
    if incidencia.estado == EstadoIncidencia.CERRADA:
        raise ValidationError({"incidencia_id": "No se puede notificar una incidencia cerrada."})
    return incidencia


def _datos_contexto(incidencia):
    if incidencia is None:
        return {}
    return {
        "incidencia_id": incidencia.id,
        "matricula_id": incidencia.matricula_id,
        "estudiante_codigo": incidencia.matricula.estudiante.codigo_estudiante,
    }


def _registrar_fallo(notificacion, detalle):
    notificacion.estado_envio = EstadoEnvio.FALLIDA
    notificacion.fecha_envio = timezone.now()
    notificacion.detalle_error = detalle[:250]
    notificacion.save(update_fields=["estado_envio", "fecha_envio", "detalle_error"])
    return notificacion


def _enviar_correo_sendgrid(notificacion):
    destinatario = notificacion.destinatario
    if destinatario is None and notificacion.apoderado_id:
        destinatario = notificacion.apoderado.perfil.user
    if destinatario is None:
        raise CorreoError("La notificacion no tiene un destinatario valido.")

    rol = get_primary_role(destinatario)
    ruta = notificacion.accion_url or RUTAS_NOTIFICACIONES.get(rol, "/notificaciones")
    accion_url = f"{settings.FRONTEND_URL.rstrip('/')}/{ruta.lstrip('/')}"
    contenido = renderizar_correo(
        destinatario=destinatario,
        rol=rol,
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
