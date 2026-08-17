from rest_framework.decorators import action
from rest_framework.response import Response

from sga.models import EstadoEnvio, Notificacion
from sga.serializers import NotificacionSerializer, NotificacionEstadoSerializer
from sga.services.notificaciones import enviar_notificacion, marcar_como_leida

from .base import AdminCatalogViewSet


class NotificacionViewSet(AdminCatalogViewSet):
    logical_delete_field = "activo"
    logical_delete_value = False
    logical_delete_message = "Notificacion desactivada correctamente."
    queryset = Notificacion.objects.select_related(
        "incidencia__matricula__estudiante__perfil__user",
        "incidencia__matricula__seccion__grado",
        "apoderado__perfil__user",
    ).order_by("-id")
    serializer_class = NotificacionSerializer
    search_fields = (
        "titulo",
        "mensaje",
        "estado_envio",
        "incidencia__descripcion",
        "incidencia__matricula__estudiante__codigo_estudiante",
        "incidencia__matricula__estudiante__perfil__dni",
        "incidencia__matricula__estudiante__perfil__user__first_name",
        "incidencia__matricula__estudiante__perfil__user__last_name",
        "apoderado__perfil__dni",
        "apoderado__perfil__user__first_name",
        "apoderado__perfil__user__last_name",
        "apoderado__perfil__user__email",
    )
    ordering_fields = ("estado_envio", "fecha_envio", "fecha_lectura", "activo")

    def get_queryset(self):
        queryset = super().get_queryset()
        filters_map = {
            "incidencia": "incidencia_id",
            "apoderado": "apoderado_id",
            "estudiante": "incidencia__matricula__estudiante_id",
            "estado_envio": "estado_envio",
            "activo": "activo",
        }
        for param, field in filters_map.items():
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    def perform_create(self, serializer):
        notificacion = serializer.save(estado_envio=EstadoEnvio.PENDIENTE)
        enviar_notificacion(notificacion)

    @action(detail=True, methods=["post"], url_path="reenviar")
    def reenviar(self, request, pk=None):
        notificacion = self.get_object()
        notificacion.estado_envio = EstadoEnvio.PENDIENTE
        notificacion.fecha_envio = None
        notificacion.save(update_fields=["estado_envio", "fecha_envio"])
        enviar_notificacion(notificacion)
        return Response(NotificacionEstadoSerializer(notificacion).data)

    @action(detail=True, methods=["post"], url_path="marcar-leida")
    def marcar_leida(self, request, pk=None):
        notificacion = marcar_como_leida(self.get_object())
        return Response(NotificacionEstadoSerializer(notificacion).data)
