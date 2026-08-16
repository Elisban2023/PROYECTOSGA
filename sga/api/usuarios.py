from django.contrib.auth import get_user_model

from sga.models import Apoderado, Docente, Estudiante, VinculoApoderado
from sga.serializers import (
    ApoderadoSerializer,
    DocenteSerializer,
    EstudianteSerializer,
    UserAccountSerializer,
    VinculoApoderadoSerializer,
)

from .base import AdminCatalogViewSet, HardDeleteViewSet, UserDeactivationMixin


User = get_user_model()


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
