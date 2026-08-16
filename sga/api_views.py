from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .models import (
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Curso,
    Docente,
    Estudiante,
    Grado,
    PeriodoAcademico,
    Seccion,
    VinculoApoderado,
)
from .serializers import (
    AnioAcademicoSerializer,
    ApoderadoSerializer,
    AsignacionCursoSerializer,
    CursoSerializer,
    DocenteSerializer,
    EstudianteSerializer,
    GradoSerializer,
    PeriodoAcademicoSerializer,
    SeccionSerializer,
    UserAccountSerializer,
    UserMeSerializer,
    VinculoApoderadoSerializer,
)


User = get_user_model()


class AdminCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminUser,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    logical_delete_field = None
    logical_delete_value = None
    logical_delete_message = "Registro desactivado correctamente."

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self.apply_logical_delete(instance):
            return Response(
                {"detail": "Este recurso no permite eliminacion desde la API."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return Response({"detail": self.logical_delete_message}, status=status.HTTP_200_OK)

    def apply_logical_delete(self, instance):
        if self.logical_delete_field is None:
            return False
        setattr(instance, self.logical_delete_field, self.logical_delete_value)
        instance.save(update_fields=[self.logical_delete_field])
        return True


class HardDeleteViewSet(AdminCatalogViewSet):
    def destroy(self, request, *args, **kwargs):
        return viewsets.ModelViewSet.destroy(self, request, *args, **kwargs)


class UserDeactivationMixin:
    logical_delete_message = "Usuario desactivado correctamente."

    def apply_logical_delete(self, instance):
        user = self.get_user_for_logical_delete(instance)
        if user.is_superuser and user.pk == self.request.user.pk:
            return False
        user.is_active = False
        user.save(update_fields=["is_active"])
        return True

    def get_user_for_logical_delete(self, instance):
        return instance


class UsuarioViewSet(UserDeactivationMixin, AdminCatalogViewSet):
    queryset = User.objects.prefetch_related("groups").select_related("perfil").order_by("username")
    serializer_class = UserAccountSerializer
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "perfil__dni",
        "perfil__telefono",
        "groups__name",
    )
    ordering_fields = ("username", "first_name", "last_name", "email", "is_active", "is_staff")


class EstudianteViewSet(UserDeactivationMixin, AdminCatalogViewSet):
    def get_user_for_logical_delete(self, instance):
        return instance.perfil.user

    queryset = Estudiante.objects.select_related("perfil__user").order_by("codigo_estudiante")
    serializer_class = EstudianteSerializer
    search_fields = (
        "codigo_estudiante",
        "perfil__dni",
        "perfil__telefono",
        "perfil__user__username",
        "perfil__user__first_name",
        "perfil__user__last_name",
        "perfil__user__email",
    )
    ordering_fields = (
        "codigo_estudiante",
        "fecha_nacimiento",
        "perfil__user__first_name",
        "perfil__user__last_name",
        "perfil__user__is_active",
    )


class DocenteViewSet(UserDeactivationMixin, AdminCatalogViewSet):
    def get_user_for_logical_delete(self, instance):
        return instance.perfil.user

    queryset = Docente.objects.select_related("perfil__user").order_by(
        "perfil__user__last_name",
        "perfil__user__first_name",
    )
    serializer_class = DocenteSerializer
    search_fields = (
        "perfil__dni",
        "perfil__telefono",
        "perfil__user__username",
        "perfil__user__first_name",
        "perfil__user__last_name",
        "perfil__user__email",
    )
    ordering_fields = (
        "perfil__user__first_name",
        "perfil__user__last_name",
        "perfil__user__email",
        "perfil__user__is_active",
    )


class ApoderadoViewSet(UserDeactivationMixin, AdminCatalogViewSet):
    def get_user_for_logical_delete(self, instance):
        return instance.perfil.user

    queryset = Apoderado.objects.select_related("perfil__user").order_by(
        "perfil__user__last_name",
        "perfil__user__first_name",
    )
    serializer_class = ApoderadoSerializer
    search_fields = DocenteViewSet.search_fields
    ordering_fields = DocenteViewSet.ordering_fields


class VinculoApoderadoViewSet(HardDeleteViewSet):
    queryset = VinculoApoderado.objects.select_related(
        "apoderado__perfil__user",
        "estudiante__perfil__user",
    ).order_by("estudiante__codigo_estudiante", "-es_principal")
    serializer_class = VinculoApoderadoSerializer
    search_fields = (
        "apoderado__perfil__dni",
        "apoderado__perfil__user__first_name",
        "apoderado__perfil__user__last_name",
        "estudiante__codigo_estudiante",
        "estudiante__perfil__dni",
        "estudiante__perfil__user__first_name",
        "estudiante__perfil__user__last_name",
        "parentesco",
    )
    ordering_fields = ("parentesco", "es_principal", "estudiante__codigo_estudiante")


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
