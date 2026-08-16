from sga.models import Matricula
from sga.serializers import MatriculaSerializer

from .base import AdminCatalogViewSet


class MatriculaViewSet(AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = "RETIRADA"
    logical_delete_message = "Matricula retirada correctamente."
    queryset = Matricula.objects.select_related(
        "estudiante__perfil__user",
        "seccion__grado",
        "anio_academico",
    ).order_by("-anio_academico__anio", "seccion__grado__nombre", "seccion__nombre", "estudiante__codigo_estudiante")
    serializer_class = MatriculaSerializer
    search_fields = (
        "estudiante__codigo_estudiante",
        "estudiante__perfil__dni",
        "estudiante__perfil__user__first_name",
        "estudiante__perfil__user__last_name",
        "seccion__nombre",
        "seccion__grado__nombre",
        "seccion__grado__nivel",
        "anio_academico__anio",
        "estado",
    )
    ordering_fields = (
        "fecha_matricula",
        "estado",
        "anio_academico__anio",
        "seccion__nombre",
        "seccion__grado__nombre",
        "estudiante__codigo_estudiante",
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        filters_map = {
            "anio_academico": "anio_academico_id",
            "seccion": "seccion_id",
            "grado": "seccion__grado_id",
            "estudiante": "estudiante_id",
            "estado": "estado",
        }
        for param, field in filters_map.items():
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset
