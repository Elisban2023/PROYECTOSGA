from rest_framework import viewsets

from sga.models import Notificacion
from sga.permissions import IsAdminOrDirectivo
from sga.serializers import NotificacionSerializer


class NotificacionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAdminOrDirectivo,)
    queryset = Notificacion.objects.select_related(
        "incidencia__matricula__estudiante__perfil__user",
        "incidencia__matricula__seccion__grado",
        "recomendacion__matricula__estudiante__perfil__user",
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
