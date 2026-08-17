from rest_framework.permissions import BasePermission

from .roles import (
    ROLE_APODERADO,
    ROLE_DOCENTE,
    ROLE_ESTUDIANTE,
    has_any_role,
    is_admin_or_directivo,
)


class IsAdminOrDirectivo(BasePermission):
    def has_permission(self, request, view):
        return is_admin_or_directivo(request.user)


class IsDocente(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, {ROLE_DOCENTE})


class IsEstudiante(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, {ROLE_ESTUDIANTE})


class IsApoderado(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, {ROLE_APODERADO})


class IsAdminOrDirectivoOrDocente(BasePermission):
    def has_permission(self, request, view):
        return is_admin_or_directivo(request.user) or has_any_role(request.user, {ROLE_DOCENTE})
