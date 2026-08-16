from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import filters, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import (
    AnioAcademico,
    AsignacionCurso,
    Curso,
    Grado,
    PeriodoAcademico,
    Seccion,
)
from .serializers import (
    AnioAcademicoSerializer,
    AsignacionCursoSerializer,
    CursoSerializer,
    GradoSerializer,
    PeriodoAcademicoSerializer,
    SeccionSerializer,
    UserMeSerializer,
)


class AdminCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminUser,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)


class AnioAcademicoViewSet(AdminCatalogViewSet):
    queryset = AnioAcademico.objects.all().order_by("-anio")
    serializer_class = AnioAcademicoSerializer
    search_fields = ("anio", "estado")
    ordering_fields = ("anio", "fecha_inicio", "fecha_fin", "estado")


class PeriodoAcademicoViewSet(AdminCatalogViewSet):
    queryset = PeriodoAcademico.objects.select_related("anio_academico").order_by(
        "-anio_academico__anio",
        "fecha_inicio",
    )
    serializer_class = PeriodoAcademicoSerializer
    search_fields = ("nombre", "estado", "anio_academico__anio")
    ordering_fields = ("nombre", "fecha_inicio", "fecha_fin", "estado")


class GradoViewSet(AdminCatalogViewSet):
    queryset = Grado.objects.all().order_by("nivel", "nombre")
    serializer_class = GradoSerializer
    search_fields = ("nombre", "nivel")
    ordering_fields = ("nombre", "nivel")


class SeccionViewSet(AdminCatalogViewSet):
    queryset = Seccion.objects.select_related("grado").order_by("grado__nivel", "grado__nombre", "nombre")
    serializer_class = SeccionSerializer
    search_fields = ("nombre", "grado__nombre", "grado__nivel")
    ordering_fields = ("nombre", "grado__nombre", "grado__nivel")


class CursoViewSet(AdminCatalogViewSet):
    queryset = Curso.objects.all().order_by("nombre")
    serializer_class = CursoSerializer
    search_fields = ("nombre", "descripcion")
    ordering_fields = ("nombre", "estado")


class AsignacionCursoViewSet(AdminCatalogViewSet):
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


@extend_schema(responses=UserMeSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    serializer = UserMeSerializer(request.user)
    return Response(serializer.data)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def menu(request):
    user = request.user
    is_admin = user.is_staff or user.is_superuser or user.groups.filter(name__in=["Administrador", "Directivo"]).exists()

    if is_admin:
        items = [
            {"label": "Dashboard", "path": "/dashboard"},
            {
                "label": "Gestion academica",
                "children": [
                    {"label": "Anios academicos", "path": "/gestion-academica/anios-academicos"},
                    {"label": "Periodos", "path": "/gestion-academica/periodos"},
                    {"label": "Grados y secciones", "path": "/gestion-academica/grados-secciones"},
                    {"label": "Cursos", "path": "/gestion-academica/cursos"},
                    {"label": "Asignacion de cursos", "path": "/gestion-academica/asignaciones-cursos"},
                ],
            },
            {
                "label": "Usuarios",
                "children": [
                    {"label": "Estudiantes", "path": "/usuarios/estudiantes"},
                    {"label": "Docentes", "path": "/usuarios/docentes"},
                    {"label": "Apoderados", "path": "/usuarios/apoderados"},
                    {"label": "Usuarios y roles", "path": "/usuarios/roles"},
                ],
            },
            {"label": "Matriculas", "path": "/matriculas"},
            {
                "label": "Seguimiento",
                "children": [
                    {"label": "Incidencias", "path": "/seguimiento/incidencias"},
                    {"label": "Observaciones", "path": "/seguimiento/observaciones"},
                    {"label": "Recomendaciones IA", "path": "/seguimiento/recomendaciones-ia"},
                ],
            },
            {"label": "Reportes", "path": "/reportes"},
            {"label": "Auditoria", "path": "/auditoria"},
            {"label": "Configuracion", "path": "/configuracion"},
        ]
    else:
        items = [{"label": "Dashboard", "path": "/dashboard"}]

    return Response({"items": items})
