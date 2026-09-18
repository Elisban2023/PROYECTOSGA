from drf_spectacular.utils import OpenApiTypes, extend_schema
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from sga.models import RegistroAuditoria, TipoBackup
from sga.permissions import IsAdminOrDirectivo
from sga.serializers.archivos_cloud import (
    BackupBaseDatosSerializer,
    CrearBackupSerializer,
    EliminarBackupSerializer,
    RestaurarBackupSerializer,
)
from sga.services.backups import (
    eliminar_backup,
    get_backups,
    obtener_url_descarga_backup,
    programar_backup,
    restaurar_backup,
    solicitar_backup,
)


class BackupRateThrottle(UserRateThrottle):
    scope = "backup"


class RestoreRateThrottle(UserRateThrottle):
    scope = "restore"


@extend_schema(responses=BackupBaseDatosSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def backups_administracion(request):
    paginator = PageNumberPagination()
    pagina = paginator.paginate_queryset(get_backups(), request)
    response = paginator.get_paginated_response(BackupBaseDatosSerializer(pagina, many=True).data)
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@extend_schema(
    methods=["GET"],
    responses=BackupBaseDatosSerializer,
)
@extend_schema(
    methods=["DELETE"],
    request=EliminarBackupSerializer,
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["GET", "DELETE"])
@permission_classes([IsAdminOrDirectivo])
def detalle_backup_administracion(request, backup_id):
    backup = get_object_or_404(get_backups(), pk=backup_id)
    if request.method == "DELETE":
        _exigir_superusuario(request.user)
        serializer = EliminarBackupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        eliminado = eliminar_backup(backup=backup)
        RegistroAuditoria.registrar_evento(
            user=request.user,
            accion="ELIMINAR_BACKUP",
            modulo="configuracion",
            entidad="BackupBaseDatos",
            entidad_id=str(eliminado.id),
        )
        return Response(
            {
                "detail": "El respaldo fue eliminado correctamente.",
                "id": eliminado.id,
                "estado": eliminado.estado,
            }
        )
    response = Response(BackupBaseDatosSerializer(backup).data)
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@extend_schema(request=CrearBackupSerializer, responses={202: BackupBaseDatosSerializer})
@api_view(["POST"])
@permission_classes([IsAdminOrDirectivo])
@throttle_classes([BackupRateThrottle])
def crear_backup_administracion(request):
    serializer = CrearBackupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    backup = solicitar_backup(user=request.user, tipo=TipoBackup.MANUAL)
    try:
        programar_backup(backup.id)
    except Exception as exc:
        backup.estado = "ERROR"
        backup.detalle_error = "No se pudo iniciar el procesamiento del respaldo."
        backup.save(update_fields=["estado", "detalle_error"])
        raise APIException("No se pudo iniciar el respaldo.") from exc
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="CREAR_BACKUP_MANUAL",
        modulo="configuracion",
        entidad="BackupBaseDatos",
        entidad_id=str(backup.id),
    )
    response = Response(BackupBaseDatosSerializer(backup).data, status=status.HTTP_202_ACCEPTED)
    response["Location"] = f"/api/administracion/backups/{backup.id}/"
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def descargar_backup_administracion(request, backup_id):
    _exigir_superusuario(request.user)
    backup = get_object_or_404(get_backups(), pk=backup_id)
    signed_url = obtener_url_descarga_backup(backup)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="GENERAR_URL_DESCARGA_BACKUP",
        modulo="configuracion",
        entidad="BackupBaseDatos",
        entidad_id=str(backup.id),
    )
    return Response({"url": signed_url, "uso_inmediato": True})


@extend_schema(request=RestaurarBackupSerializer, responses=OpenApiTypes.OBJECT)
@api_view(["POST"])
@permission_classes([IsAdminOrDirectivo])
@throttle_classes([RestoreRateThrottle])
def restaurar_backup_administracion(request, backup_id):
    _exigir_superusuario(request.user)
    serializer = RestaurarBackupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    backup = get_object_or_404(get_backups(), pk=backup_id)
    try:
        restaurado, respaldo_previo = restaurar_backup(user=request.user, backup=backup)
    except Exception as exc:
        raise APIException(
            "No se pudo restaurar el respaldo. La operacion fue cancelada y debe revisarse en auditoria."
        ) from exc
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="RESTAURAR_BACKUP",
        modulo="configuracion",
        entidad="BackupBaseDatos",
        entidad_id=str(restaurado.id),
    )
    return Response(
        {
            "backup": BackupBaseDatosSerializer(restaurado).data,
            "backup_pre_restauracion_id": respaldo_previo.id,
        }
    )


def _exigir_superusuario(user):
    if not user.is_superuser:
        raise PermissionDenied("Solo el propietario superusuario puede acceder al contenido del respaldo.")
