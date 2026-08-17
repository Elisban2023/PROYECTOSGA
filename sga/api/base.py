from rest_framework import filters, status, viewsets
from rest_framework.response import Response

from sga.permissions import IsAdminOrDirectivo


class AdminCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrDirectivo,)
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
