from django.utils import timezone

from sga.models import IncidenciaAcademica, ObservacionAcademica
from sga.serializers import IncidenciaAcademicaSerializer, ObservacionAcademicaSerializer

from .base import AdminCatalogViewSet


class ObservacionAcademicaViewSet(AdminCatalogViewSet):
    logical_delete_field = "activo"
    logical_delete_value = False
    logical_delete_message = "Observacion desactivada correctamente."
    queryset = ObservacionAcademica.objects.select_related(
        "matricula__estudiante__perfil__user",
        "matricula__seccion__grado",
        "matricula__anio_academico",
        "asignacion_curso__curso",
        "asignacion_curso__seccion__grado",
        "asignacion_curso__anio_academico",
        "docente__perfil__user",
    ).order_by("-fecha")
    serializer_class = ObservacionAcademicaSerializer
    search_fields = (
        "categoria",
        "descripcion",
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__dni",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "docente__perfil__user__first_name",
        "docente__perfil__user__last_name",
        "asignacion_curso__curso__nombre",
    )
    ordering_fields = ("fecha", "categoria", "activo")

    def get_queryset(self):
        queryset = super().get_queryset()
        filters_map = {
            "matricula": "matricula_id",
            "estudiante": "matricula__estudiante_id",
            "docente": "docente_id",
            "asignacion_curso": "asignacion_curso_id",
            "activo": "activo",
        }
        for param, field in filters_map.items():
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


class IncidenciaAcademicaViewSet(AdminCatalogViewSet):
    logical_delete_message = "Incidencia cerrada correctamente."
    queryset = IncidenciaAcademica.objects.select_related(
        "matricula__estudiante__perfil__user",
        "matricula__seccion__grado",
        "matricula__anio_academico",
        "observacion",
    ).order_by("-fecha_registro")
    serializer_class = IncidenciaAcademicaSerializer
    search_fields = (
        "descripcion",
        "tipo",
        "nivel",
        "estado",
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__dni",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
    )
    ordering_fields = ("fecha_registro", "fecha_cierre", "tipo", "nivel", "estado")

    def apply_logical_delete(self, instance):
        instance.estado = "CERRADA"
        if instance.fecha_cierre is None:
            instance.fecha_cierre = timezone.now()
        instance.save(update_fields=["estado", "fecha_cierre"])
        return True

    def get_queryset(self):
        queryset = super().get_queryset()
        filters_map = {
            "matricula": "matricula_id",
            "estudiante": "matricula__estudiante_id",
            "observacion": "observacion_id",
            "tipo": "tipo",
            "nivel": "nivel",
            "estado": "estado",
        }
        for param, field in filters_map.items():
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset
