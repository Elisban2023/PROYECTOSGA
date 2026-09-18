import hashlib
import uuid
from datetime import timedelta
from pathlib import PurePath

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from sga.models import (
    ArchivoCloud,
    EstadoArchivoCloud,
    EstadoAsistencia,
    EstadoEnvio,
    EstadoJustificacion,
    JustificacionInasistencia,
    Notificacion,
    PrioridadNotificacion,
    TipoArchivoCloud,
    TipoNotificacion,
)
from sga.roles import is_admin_or_directivo
from sga.services.apoderado import get_vinculos_apoderado
from sga.services.aws_signed_urls import AwsSignedURLService
from sga.services.docente import get_asignaciones_docente
from sga.services.notificaciones import crear_notificaciones_docente, enviar_notificacion


MIME_EXTENSIONES = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
}


def get_justificaciones_apoderado(user):
    apoderado = getattr(getattr(user, "perfil", None), "apoderado", None)
    if apoderado is None:
        return JustificacionInasistencia.objects.none()
    return _queryset_base().filter(apoderado=apoderado).exclude(
        estado=EstadoJustificacion.ELIMINADA
    )


def get_justificaciones_docente(user):
    asignaciones_ids = get_asignaciones_docente(user).values_list("id", flat=True)
    return _queryset_base().filter(
        asistencia__asignacion_curso_id__in=asignaciones_ids,
    ).exclude(estado=EstadoJustificacion.ELIMINADA)


def get_justificaciones_estudiante(user):
    estudiante = getattr(getattr(user, "perfil", None), "estudiante", None)
    if estudiante is None:
        return JustificacionInasistencia.objects.none()
    return _queryset_base().filter(
        asistencia__matricula__estudiante=estudiante,
    ).exclude(
        estado__in=(
            EstadoJustificacion.PENDIENTE_CARGA,
            EstadoJustificacion.ELIMINADA,
        )
    )


def get_justificaciones_administracion():
    return _queryset_base().exclude(estado=EstadoJustificacion.ELIMINADA)


def solicitar_carga_justificacion(user, *, asistencia_id, nombre_archivo, mime_type, tamano, motivo):
    vinculos = get_vinculos_apoderado(user)
    apoderado = getattr(getattr(user, "perfil", None), "apoderado", None)
    asistencia = (
        _queryset_asistencias()
        .filter(
            pk=asistencia_id,
            matricula__estudiante_id__in=vinculos.values("estudiante_id"),
        )
        .first()
    )
    if asistencia is None or apoderado is None:
        raise ValidationError({"asistencia_id": "La asistencia no pertenece a un estudiante vinculado."})
    if asistencia.estado not in (EstadoAsistencia.FALTA, EstadoAsistencia.TARDE):
        raise ValidationError(
            {"asistencia_id": "Solo se pueden justificar faltas o tardanzas registradas."}
        )

    _expirar_cargas_pendientes(asistencia)
    if JustificacionInasistencia.objects.filter(
        asistencia=asistencia,
        estado__in=(
            EstadoJustificacion.PENDIENTE_CARGA,
            EstadoJustificacion.PENDIENTE_REVISION,
            EstadoJustificacion.APROBADA,
        ),
    ).exists():
        raise ValidationError(
            {"asistencia_id": "Ya existe una justificacion activa para esta asistencia."}
        )

    extension = MIME_EXTENSIONES[mime_type]
    nombre_seguro = PurePath(nombre_archivo).name[:255]
    clave_s3 = (
        f"{settings.AWS_S3_PREFIX}/justificaciones/"
        f"{asistencia.fecha.year}/{uuid.uuid4().hex}.{extension}"
    )
    with transaction.atomic():
        archivo = ArchivoCloud.objects.create(
            tipo=TipoArchivoCloud.JUSTIFICACION,
            clave_s3=clave_s3,
            nombre_original=nombre_seguro,
            mime_type=mime_type,
            extension=extension,
            tamano=tamano,
            creado_por=user,
        )
        justificacion = JustificacionInasistencia.objects.create(
            asistencia=asistencia,
            apoderado=apoderado,
            archivo=archivo,
            motivo=motivo,
        )

    try:
        signed_url = AwsSignedURLService().obtener_url_carga(clave_s3)
    except Exception:
        archivo.estado = EstadoArchivoCloud.ERROR
        archivo.save(update_fields=["estado"])
        justificacion.estado = EstadoJustificacion.ELIMINADA
        justificacion.save(update_fields=["estado"])
        raise

    return justificacion, signed_url


def confirmar_carga_justificacion(user, justificacion):
    apoderado = getattr(getattr(user, "perfil", None), "apoderado", None)
    if apoderado is None or justificacion.apoderado_id != apoderado.id:
        raise PermissionDenied("No puede confirmar esta justificacion.")
    if justificacion.estado != EstadoJustificacion.PENDIENTE_CARGA:
        raise ValidationError({"detalle": "La carga ya fue confirmada o dejo de estar vigente."})

    archivo = justificacion.archivo
    contenido = AwsSignedURLService().descargar_bytes(
        archivo.clave_s3,
        limite=settings.AWS_S3_MAX_JUSTIFICACION_BYTES,
    )
    if len(contenido) != archivo.tamano:
        raise ValidationError(
            {"archivo": "El tamano cargado no coincide con el tamano declarado."}
        )
    if not _firma_archivo_valida(archivo.mime_type, contenido):
        raise ValidationError(
            {"archivo": "El contenido no corresponde a un PDF, JPEG o PNG valido."}
        )

    with transaction.atomic():
        archivo.sha256 = hashlib.sha256(contenido).hexdigest()
        archivo.estado = EstadoArchivoCloud.DISPONIBLE
        archivo.fecha_confirmacion = timezone.now()
        archivo.save(update_fields=["sha256", "estado", "fecha_confirmacion"])
        justificacion.estado = EstadoJustificacion.PENDIENTE_REVISION
        justificacion.save(update_fields=["estado"])

    docente_user = justificacion.asistencia.asignacion_curso.docente.perfil.user
    notificacion = Notificacion.objects.create(
        destinatario=docente_user,
        tipo=TipoNotificacion.ASISTENCIA,
        prioridad=PrioridadNotificacion.NORMAL,
        titulo="Nueva justificacion de inasistencia",
        mensaje="Un apoderado envio un sustento que requiere revision docente.",
        accion_url="/docente/justificaciones",
        datos={
            "justificacion_id": justificacion.id,
            "asistencia_id": justificacion.asistencia_id,
            "asignacion_curso_id": justificacion.asistencia.asignacion_curso_id,
        },
        estado_envio=EstadoEnvio.PENDIENTE,
    )
    enviar_notificacion(notificacion)
    return justificacion


def revisar_justificacion(user, justificacion, *, estado, comentario):
    docente = getattr(getattr(user, "perfil", None), "docente", None)
    if (
        docente is None
        or justificacion.asistencia.asignacion_curso.docente_id != docente.id
    ):
        raise PermissionDenied("La justificacion no pertenece a uno de sus cursos.")
    if justificacion.estado != EstadoJustificacion.PENDIENTE_REVISION:
        raise ValidationError({"estado": "La justificacion ya fue revisada o no esta confirmada."})

    with transaction.atomic():
        justificacion.estado = estado
        justificacion.revisado_por = docente
        justificacion.comentario_revision = comentario
        justificacion.fecha_revision = timezone.now()
        justificacion.save(
            update_fields=(
                "estado",
                "revisado_por",
                "comentario_revision",
                "fecha_revision",
            )
        )
        if estado == EstadoJustificacion.APROBADA:
            asistencia = justificacion.asistencia
            asistencia.estado = EstadoAsistencia.JUSTIFICADA
            asistencia.justificacion = justificacion.motivo[:500]
            asistencia.save(update_fields=["estado", "justificacion"])

    usuarios_destino = (
        justificacion.apoderado.perfil.user,
        justificacion.asistencia.matricula.estudiante.perfil.user,
    )
    destinatarios = list(
        dict.fromkeys(usuario.id for usuario in usuarios_destino if usuario.is_active)
    )
    resultado = "aprobada" if estado == EstadoJustificacion.APROBADA else "rechazada"
    if destinatarios:
        crear_notificaciones_docente(
            user,
            destinatarios=destinatarios,
            titulo=f"Justificacion de inasistencia {resultado}",
            mensaje=(
                f"La justificacion fue {resultado}. Comentario del docente: {comentario}"
            ),
            tipo=TipoNotificacion.ASISTENCIA,
            prioridad=PrioridadNotificacion.NORMAL,
            datos_extra={
                "justificacion_id": justificacion.id,
                "asistencia_id": justificacion.asistencia_id,
            },
        )
    return justificacion


def obtener_url_descarga_autorizada(user, justificacion):
    if not _puede_ver_justificacion(user, justificacion):
        raise PermissionDenied("No tiene acceso a este archivo.")
    archivo = justificacion.archivo
    if archivo.estado != EstadoArchivoCloud.DISPONIBLE:
        raise ValidationError({"archivo": "El archivo no esta disponible."})
    return AwsSignedURLService().obtener_url_descarga(archivo.clave_s3)


def eliminar_justificacion(user, justificacion):
    apoderado = getattr(getattr(user, "perfil", None), "apoderado", None)
    if apoderado is None or justificacion.apoderado_id != apoderado.id:
        raise PermissionDenied("No puede retirar esta justificacion.")
    if justificacion.estado not in (
        EstadoJustificacion.PENDIENTE_CARGA,
        EstadoJustificacion.RECHAZADA,
    ):
        raise ValidationError(
            {"estado": "Solo se pueden retirar cargas pendientes o justificaciones rechazadas."}
        )
    archivo = justificacion.archivo
    error_cloud = False
    try:
        AwsSignedURLService().eliminar_objeto(archivo.clave_s3)
    except Exception:
        error_cloud = True

    ahora = timezone.now()
    with transaction.atomic():
        justificacion.estado = EstadoJustificacion.ELIMINADA
        justificacion.save(update_fields=["estado"])
        archivo.estado = EstadoArchivoCloud.ELIMINADO
        archivo.fecha_eliminacion = ahora
        archivo.save(update_fields=["estado", "fecha_eliminacion"])
    return error_cloud


def _queryset_base():
    return JustificacionInasistencia.objects.select_related(
        "asistencia__matricula__estudiante__perfil__user",
        "asistencia__asignacion_curso__curso",
        "asistencia__asignacion_curso__docente__perfil__user",
        "apoderado__perfil__user",
        "archivo",
        "revisado_por__perfil__user",
    )


def _queryset_asistencias():
    from sga.models import Asistencia

    return Asistencia.objects.select_related(
        "matricula__estudiante__perfil__user",
        "asignacion_curso__curso",
        "asignacion_curso__docente__perfil__user",
    )


def _expirar_cargas_pendientes(asistencia):
    limite = timezone.now() - timedelta(minutes=settings.AWS_S3_UPLOAD_PENDING_TTL_MINUTES)
    pendientes = JustificacionInasistencia.objects.filter(
        asistencia=asistencia,
        estado=EstadoJustificacion.PENDIENTE_CARGA,
        fecha_solicitud__lt=limite,
    ).select_related("archivo")
    servicio = None
    for item in pendientes:
        try:
            servicio = servicio or AwsSignedURLService()
            servicio.eliminar_objeto(item.archivo.clave_s3)
        except Exception:
            pass
        item.estado = EstadoJustificacion.ELIMINADA
        item.archivo.estado = EstadoArchivoCloud.ELIMINADO
        item.archivo.fecha_eliminacion = timezone.now()
        item.archivo.save(update_fields=["estado", "fecha_eliminacion"])
        item.save(update_fields=["estado"])


def _firma_archivo_valida(mime_type, contenido):
    if mime_type == "application/pdf":
        return contenido.startswith(b"%PDF-")
    if mime_type == "image/png":
        return contenido.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return contenido.startswith(b"\xff\xd8\xff") and contenido.endswith(b"\xff\xd9")
    return False


def _puede_ver_justificacion(user, justificacion):
    if is_admin_or_directivo(user):
        return True
    perfil = getattr(user, "perfil", None)
    if perfil is None:
        return False
    if getattr(perfil, "apoderado", None) == justificacion.apoderado:
        return True
    if getattr(perfil, "estudiante", None) == justificacion.asistencia.matricula.estudiante:
        return True
    docente = getattr(perfil, "docente", None)
    return bool(
        docente
        and justificacion.asistencia.asignacion_curso.docente_id == docente.id
    )
