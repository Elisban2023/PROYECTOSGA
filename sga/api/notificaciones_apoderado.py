from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from sga.models import Notificacion, RegistroAuditoria
from sga.permissions import IsApoderado
from sga.serializers.notificaciones import NotificacionEstadoSerializer, NotificacionSerializer
from sga.services.notificaciones import marcar_como_leida


def _notificaciones_apoderado(user):
    return Notificacion.objects.filter(
        apoderado=user.perfil.apoderado,
        activo=True,
    ).select_related("incidencia__matricula__estudiante__perfil__user", "apoderado__perfil__user").order_by("-id")


@extend_schema(responses=NotificacionSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsApoderado])
def mis_notificaciones(request):
    queryset = _notificaciones_apoderado(request.user)
    estado = request.query_params.get("estado_envio")
    if estado:
        queryset = queryset.filter(estado_envio=estado)
    return Response(NotificacionSerializer(queryset, many=True).data)


@extend_schema(responses=NotificacionEstadoSerializer)
@api_view(["POST"])
@permission_classes([IsApoderado])
def marcar_notificacion_leida(request, notificacion_id):
    notificacion = get_object_or_404(_notificaciones_apoderado(request.user), pk=notificacion_id)
    notificacion = marcar_como_leida(notificacion)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="MARCAR_NOTIFICACION_LEIDA",
        modulo="apoderado",
        entidad="Notificacion",
        entidad_id=str(notificacion.id),
    )
    return Response(NotificacionEstadoSerializer(notificacion).data)
