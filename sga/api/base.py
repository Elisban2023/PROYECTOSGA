from rest_framework import filters, status, viewsets
from rest_framework.response import Response

from sga.models import RegistroAuditoria
from sga.permissions import IsAdminOrDirectivo


class AdminCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrDirectivo,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    logical_delete_field = None
    logical_delete_value = None
    logical_delete_message = "Registro desactivado correctamente."

    def perform_create(self, serializer):
        instance = serializer.save()
        self.registrar_auditoria("CREAR", instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.registrar_auditoria("ACTUALIZAR", instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self.apply_logical_delete(instance):
            return Response(
                {"detail": "Este recurso no permite eliminacion desde la API."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        self.registrar_auditoria("ELIMINAR_LOGICO", instance)
        return Response({"detail": self.logical_delete_message}, status=status.HTTP_200_OK)

    def apply_logical_delete(self, instance):
        if self.logical_delete_field is None:
            return False
        setattr(instance, self.logical_delete_field, self.logical_delete_value)
        instance.save(update_fields=[self.logical_delete_field])
        return True

    def registrar_auditoria(self, accion, instance=None):
        RegistroAuditoria.registrar_evento(
            user=self.request.user if self.request.user.is_authenticated else None,
            accion=accion,
            modulo=self.get_audit_modulo(),
            entidad=self.get_audit_entidad(instance),
            entidad_id=self.get_audit_entidad_id(instance),
        )

    def get_audit_modulo(self):
        return getattr(self, "audit_modulo", None) or getattr(self, "basename", "sga")

    def get_audit_entidad(self, instance=None):
        if instance is not None:
            return instance.__class__.__name__
        queryset = getattr(self, "queryset", None)
        if queryset is not None:
            return queryset.model.__name__
        return self.__class__.__name__

    def get_audit_entidad_id(self, instance=None):
        entidad_id = getattr(instance, "pk", None) if instance is not None else None
        return str(entidad_id) if entidad_id is not None else None


class HardDeleteViewSet(AdminCatalogViewSet):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.registrar_auditoria("ELIMINAR_FISICO", instance)
        return viewsets.ModelViewSet.destroy(self, request, *args, **kwargs)


class UserDeactivationMixin:
    logical_delete_message = "Usuario desactivado correctamente."

    def apply_logical_delete(self, instance):
        user = self.get_user_for_logical_delete(instance)
        if user.is_superuser:
            return False
        if user.pk == self.request.user.pk:
            return False
        user.is_active = False
        user.save(update_fields=["is_active"])
        return True

    def get_user_for_logical_delete(self, instance):
        return instance
