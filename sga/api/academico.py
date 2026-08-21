from rest_framework.exceptions import ValidationError

from sga.models import (
    AnioAcademico,
    AsignacionCurso,
    Curso,
    EstadoAcademico,
    EstadoGeneral,
    EstadoRegistro,
    Grado,
    PeriodoAcademico,
    Seccion,
)
from sga.serializers import (
    AnioAcademicoSerializer,
    AsignacionCursoSerializer,
    CursoSerializer,
    GradoSerializer,
    PeriodoAcademicoSerializer,
    SeccionSerializer,
)

from .base import AdminCatalogViewSet


class EstadoFilterMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.query_params.get("estado")
        if estado is None:
            return queryset
        try:
            estado = int(estado)
        except (TypeError, ValueError):
            raise ValidationError({"estado": "El estado debe ser un numero entero."})
        return queryset.filter(estado=estado)


class AnioAcademicoViewSet(EstadoFilterMixin, AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = EstadoAcademico.INACTIVO
    queryset = AnioAcademico.objects.all().order_by("-anio")
    serializer_class = AnioAcademicoSerializer
    search_fields = ("anio",)
    ordering_fields = ("anio", "fecha_inicio", "fecha_fin", "estado")


class PeriodoAcademicoViewSet(EstadoFilterMixin, AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = EstadoAcademico.INACTIVO
    queryset = PeriodoAcademico.objects.select_related("anio_academico").order_by(
        "-anio_academico__anio",
        "fecha_inicio",
    )
    serializer_class = PeriodoAcademicoSerializer
    search_fields = ("nombre", "anio_academico__anio")
    ordering_fields = ("nombre", "fecha_inicio", "fecha_fin", "estado")


class GradoViewSet(EstadoFilterMixin, AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = EstadoRegistro.INACTIVO
    queryset = Grado.objects.all().order_by("nivel", "nombre")
    serializer_class = GradoSerializer
    search_fields = ("nombre", "nivel")
    ordering_fields = ("nombre", "nivel", "estado")


class SeccionViewSet(EstadoFilterMixin, AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = EstadoRegistro.INACTIVO
    queryset = Seccion.objects.select_related("grado").order_by("grado__nivel", "grado__nombre", "nombre")
    serializer_class = SeccionSerializer
    search_fields = ("nombre", "grado__nombre", "grado__nivel")
    ordering_fields = ("nombre", "grado__nombre", "grado__nivel", "estado")


class CursoViewSet(EstadoFilterMixin, AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = EstadoRegistro.INACTIVO
    queryset = Curso.objects.all().order_by("nombre")
    serializer_class = CursoSerializer
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "estado")


class AsignacionCursoViewSet(EstadoFilterMixin, AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = EstadoGeneral.INACTIVO
    queryset = AsignacionCurso.objects.select_related(
        "curso",
        "docente__perfil__user",
        "seccion__grado",
        "anio_academico",
    ).order_by("-anio_academico__anio", "seccion__grado__nombre", "seccion__nombre", "curso__nombre")
    serializer_class = AsignacionCursoSerializer
    search_fields = (
        "curso__nombre",
        "docente__perfil__user__first_name",
        "docente__perfil__user__last_name",
        "seccion__nombre",
        "seccion__grado__nombre",
    )
    ordering_fields = ("estado", "curso__nombre", "seccion__nombre", "anio_academico__anio")
