from sga.models import AnioAcademico, AsignacionCurso, Curso, Grado, PeriodoAcademico, Seccion
from sga.serializers import (
    AnioAcademicoSerializer,
    AsignacionCursoSerializer,
    CursoSerializer,
    GradoSerializer,
    PeriodoAcademicoSerializer,
    SeccionSerializer,
)

from .base import AdminCatalogViewSet


class AnioAcademicoViewSet(AdminCatalogViewSet):
    logical_delete_field = "activo"
    logical_delete_value = False
    queryset = AnioAcademico.objects.all().order_by("-anio")
    serializer_class = AnioAcademicoSerializer
    search_fields = ("anio", "estado")
    ordering_fields = ("anio", "fecha_inicio", "fecha_fin", "estado", "activo")


class PeriodoAcademicoViewSet(AdminCatalogViewSet):
    logical_delete_field = "activo"
    logical_delete_value = False
    queryset = PeriodoAcademico.objects.select_related("anio_academico").order_by(
        "-anio_academico__anio",
        "fecha_inicio",
    )
    serializer_class = PeriodoAcademicoSerializer
    search_fields = ("nombre", "estado", "anio_academico__anio")
    ordering_fields = ("nombre", "fecha_inicio", "fecha_fin", "estado", "activo")


class GradoViewSet(AdminCatalogViewSet):
    logical_delete_field = "activo"
    logical_delete_value = False
    queryset = Grado.objects.all().order_by("nivel", "nombre")
    serializer_class = GradoSerializer
    search_fields = ("nombre", "nivel")
    ordering_fields = ("nombre", "nivel", "activo")


class SeccionViewSet(AdminCatalogViewSet):
    logical_delete_field = "activo"
    logical_delete_value = False
    queryset = Seccion.objects.select_related("grado").order_by("grado__nivel", "grado__nombre", "nombre")
    serializer_class = SeccionSerializer
    search_fields = ("nombre", "grado__nombre", "grado__nivel")
    ordering_fields = ("nombre", "grado__nombre", "grado__nivel", "activo")


class CursoViewSet(AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = False
    queryset = Curso.objects.all().order_by("nombre")
    serializer_class = CursoSerializer
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "estado")


class AsignacionCursoViewSet(AdminCatalogViewSet):
    logical_delete_field = "estado"
    logical_delete_value = "INACTIVO"
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
        "estado",
    )
    ordering_fields = ("estado", "curso__nombre", "seccion__nombre", "anio_academico__anio")
