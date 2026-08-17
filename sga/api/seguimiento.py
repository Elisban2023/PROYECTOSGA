from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from sga.models import Docente, EstadoRevisionIA, IncidenciaAcademica, ObservacionAcademica, RecomendacionIA
from sga.serializers import (
    IncidenciaAcademicaSerializer,
    ObservacionAcademicaSerializer,
    RecomendacionIASerializer,
)

from .base import AdminCatalogViewSet


class ObservacionAcademicaViewSet(AdminCatalogViewSet):
    logical_delete_field = "activo"
    logical_delete_value = False
    logical_delete_message = "Observacion desactivada correctamente."
    queryset = ObservacionAcademica.objects.select_related(
        "matricula__estudiante__perfil__user",
        "matricula__seccion__grado",
        "matricula__anio_academico",
        "asignacion_curso__curso",
        "asignacion_curso__seccion__grado",
        "asignacion_curso__anio_academico",
        "docente__perfil__user",
    ).order_by("-fecha")
    serializer_class = ObservacionAcademicaSerializer
    search_fields = (
        "categoria",
        "descripcion",
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__dni",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "docente__perfil__user__first_name",
        "docente__perfil__user__last_name",
        "asignacion_curso__curso__nombre",
    )
    ordering_fields = ("fecha", "categoria", "activo")

    def get_queryset(self):
        queryset = super().get_queryset()
        filters_map = {
            "matricula": "matricula_id",
            "estudiante": "matricula__estudiante_id",
            "docente": "docente_id",
            "asignacion_curso": "asignacion_curso_id",
            "activo": "activo",
        }
        for param, field in filters_map.items():
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


class IncidenciaAcademicaViewSet(AdminCatalogViewSet):
    logical_delete_message = "Incidencia cerrada correctamente."
    queryset = IncidenciaAcademica.objects.select_related(
        "matricula__estudiante__perfil__user",
        "matricula__seccion__grado",
        "matricula__anio_academico",
        "observacion",
    ).order_by("-fecha_registro")
    serializer_class = IncidenciaAcademicaSerializer
    search_fields = (
        "descripcion",
        "tipo",
        "nivel",
        "estado",
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__dni",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
    )
    ordering_fields = ("fecha_registro", "fecha_cierre", "tipo", "nivel", "estado")

    def apply_logical_delete(self, instance):
        instance.estado = "CERRADA"
        if instance.fecha_cierre is None:
            instance.fecha_cierre = timezone.now()
        instance.save(update_fields=["estado", "fecha_cierre"])
        return True

    def get_queryset(self):
        queryset = super().get_queryset()
        filters_map = {
            "matricula": "matricula_id",
            "estudiante": "matricula__estudiante_id",
            "observacion": "observacion_id",
            "tipo": "tipo",
            "nivel": "nivel",
            "estado": "estado",
        }
        for param, field in filters_map.items():
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset



class RecomendacionIAViewSet(AdminCatalogViewSet):
    logical_delete_field = "activo"
    logical_delete_value = False
    logical_delete_message = "Recomendacion IA desactivada correctamente."
    queryset = RecomendacionIA.objects.select_related(
        "matricula__estudiante__perfil__user",
        "matricula__seccion__grado",
        "matricula__anio_academico",
        "periodo_academico",
        "revisado_por_docente__perfil__user",
    ).order_by("-fecha_generacion")
    serializer_class = RecomendacionIASerializer
    search_fields = (
        "resumen_contexto",
        "texto_generado",
        "texto_revisado",
        "estado_revision",
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__dni",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "revisado_por_docente__perfil__user__first_name",
        "revisado_por_docente__perfil__user__last_name",
    )
    ordering_fields = ("fecha_generacion", "fecha_revision", "estado_revision", "activo")

    def get_queryset(self):
        queryset = super().get_queryset()
        filters_map = {
            "matricula": "matricula_id",
            "estudiante": "matricula__estudiante_id",
            "periodo_academico": "periodo_academico_id",
            "revisado_por_docente": "revisado_por_docente_id",
            "estado_revision": "estado_revision",
            "activo": "activo",
        }
        for param, field in filters_map.items():
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    @action(detail=True, methods=["post"], url_path="aprobar")
    def aprobar(self, request, pk=None):
        return self._registrar_revision(request, EstadoRevisionIA.APROBADA)

    @action(detail=True, methods=["post"], url_path="rechazar")
    def rechazar(self, request, pk=None):
        return self._registrar_revision(request, EstadoRevisionIA.RECHAZADA)

    @action(detail=True, methods=["post"], url_path="editar-revision")
    def editar_revision(self, request, pk=None):
        return self._registrar_revision(request, EstadoRevisionIA.EDITADA, requiere_texto=True)

    def _registrar_revision(self, request, estado_revision, requiere_texto=False):
        recomendacion = self.get_object()
        docente_id = request.data.get("docente")
        texto_revisado = request.data.get("texto_revisado", "")

        if not docente_id:
            return Response({"docente": "Debe indicar el docente revisor."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            docente = Docente.objects.select_related("perfil__user").get(pk=docente_id)
        except Docente.DoesNotExist:
            return Response({"docente": "El docente indicado no existe."}, status=status.HTTP_400_BAD_REQUEST)
        if not docente.perfil.user.is_active:
            return Response({"docente": "El docente revisor esta inactivo."}, status=status.HTTP_400_BAD_REQUEST)
        if requiere_texto and len(texto_revisado.strip()) < 10:
            return Response(
                {"texto_revisado": "Debe registrar un texto revisado de al menos 10 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recomendacion.revisado_por_docente = docente
        recomendacion.estado_revision = estado_revision
        recomendacion.texto_revisado = texto_revisado.strip() or recomendacion.texto_revisado
        recomendacion.fecha_revision = timezone.now()
        recomendacion.save(
            update_fields=[
                "revisado_por_docente",
                "estado_revision",
                "texto_revisado",
                "fecha_revision",
            ]
        )
        return Response(self.get_serializer(recomendacion).data)
