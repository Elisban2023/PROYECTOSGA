from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from sga.models import ConfiguracionInstitucional
from sga.serializers import ConfiguracionInstitucionalSerializer

from .base import AdminCatalogViewSet


class ConfiguracionInstitucionalViewSet(AdminCatalogViewSet):
    queryset = ConfiguracionInstitucional.objects.select_related("anio_academico_activo").order_by("id")
    serializer_class = ConfiguracionInstitucionalSerializer
    search_fields = ("nombre_institucion", "codigo_modular", "director", "email")
    ordering_fields = ("nombre_institucion", "codigo_modular", "actualizado_en", "activo")

    def create(self, request, *args, **kwargs):
        if ConfiguracionInstitucional.objects.exists():
            configuracion = ConfiguracionInstitucional.objects.select_related("anio_academico_activo").first()
            serializer = self.get_serializer(configuracion, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["get", "patch"], url_path="actual")
    def actual(self, request):
        configuracion = ConfiguracionInstitucional.objects.select_related("anio_academico_activo").first()
        if request.method == "GET":
            if configuracion is None:
                return Response({"detail": "No existe configuracion institucional registrada."}, status=status.HTTP_404_NOT_FOUND)
            return Response(self.get_serializer(configuracion).data)

        if configuracion is None:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = self.get_serializer(configuracion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
