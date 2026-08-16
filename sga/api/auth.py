from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sga.serializers import UserMeSerializer


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
