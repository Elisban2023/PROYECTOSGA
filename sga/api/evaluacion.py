from rest_framework.exceptions import ValidationError

from sga.models import (
    Capacidad,
    Competencia,
    CriterioCalificacion,
    EstadoRegistro,
)
from sga.serializers import (
    CapacidadSerializer,
    CompetenciaSerializer,
    CriterioCalificacionSerializer,
)

from .base import AdminCatalogViewSet


class CatalogoEvaluacionFilterMixin:
    related_filters = {}

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self._get_integer_query_param("estado")
        if estado is not None:
            queryset = queryset.filter(estado=estado)

        for param, lookup in self.related_filters.items():
            value = self._get_integer_query_param(param)
            if value is not None:
                queryset = queryset.filter(**{lookup: value})
        return queryset

    def _get_integer_query_param(self, name):
        value = self.request.query_params.get(name)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError({name: "Debe ser un numero entero."})


class CompetenciaViewSet(
    CatalogoEvaluacionFilterMixin,
    AdminCatalogViewSet,
):
    logical_delete_field = "estado"
    logical_delete_value = EstadoRegistro.INACTIVO
    queryset = Competencia.objects.select_related("curso").order_by(
        "curso__nombre",
        "nombre",
    )
    serializer_class = CompetenciaSerializer
    related_filters = {"curso": "curso_id"}
    search_fields = ("nombre", "curso__nombre")
    ordering_fields = ("nombre", "curso__nombre", "estado")


class CapacidadViewSet(
    CatalogoEvaluacionFilterMixin,
    AdminCatalogViewSet,
):
    logical_delete_field = "estado"
    logical_delete_value = EstadoRegistro.INACTIVO
    queryset = Capacidad.objects.select_related(
        "competencia__curso"
    ).order_by("competencia__curso__nombre", "competencia__nombre", "nombre")
    serializer_class = CapacidadSerializer
    related_filters = {
        "competencia": "competencia_id",
        "curso": "competencia__curso_id",
    }
    search_fields = ("nombre", "competencia__nombre", "competencia__curso__nombre")
    ordering_fields = (
        "nombre",
        "competencia__nombre",
        "competencia__curso__nombre",
        "estado",
    )


class CriterioCalificacionViewSet(
    CatalogoEvaluacionFilterMixin,
    AdminCatalogViewSet,
):
    logical_delete_field = "estado"
    logical_delete_value = EstadoRegistro.INACTIVO
    queryset = CriterioCalificacion.objects.select_related(
        "capacidad__competencia__curso"
    ).order_by(
        "capacidad__competencia__curso__nombre",
        "capacidad__competencia__nombre",
        "capacidad__nombre",
        "nombre",
    )
    serializer_class = CriterioCalificacionSerializer
    related_filters = {
        "capacidad": "capacidad_id",
        "competencia": "capacidad__competencia_id",
        "curso": "capacidad__competencia__curso_id",
    }
    search_fields = (
        "nombre",
        "descripcion",
        "capacidad__nombre",
        "capacidad__competencia__nombre",
        "capacidad__competencia__curso__nombre",
    )
    ordering_fields = (
        "nombre",
        "capacidad__nombre",
        "capacidad__competencia__nombre",
        "capacidad__competencia__curso__nombre",
        "estado",
    )
