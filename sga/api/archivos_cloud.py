from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sga.models import EstadoJustificacion, JustificacionInasistencia, RegistroAuditoria
from sga.permissions import IsAdminOrDirectivo, IsApoderado, IsDocente, IsEstudiante
from sga.serializers.archivos_cloud import (
    ConfirmarCargaSerializer,
    JustificacionInasistenciaSerializer,
    RevisarJustificacionSerializer,
    SolicitarCargaJustificacionSerializer,
)
from sga.services.justificaciones import (
    confirmar_carga_justificacion,
    eliminar_justificacion,
    get_justificaciones_administracion,
    get_justificaciones_apoderado,
    get_justificaciones_docente,
    get_justificaciones_estudiante,
    obtener_url_descarga_autorizada,
    revisar_justificacion,
    solicitar_carga_justificacion,
)
from sga.services.aws_signed_urls import obtener_headers_carga


FILTROS_JUSTIFICACIONES = [
    OpenApiParameter("estado", str, description="Estado de la justificacion."),
    OpenApiParameter("asignacion_curso", int, description="Asignacion de curso."),
    OpenApiParameter("estudiante", int, description="Estudiante."),
]


def _respuesta_paginada(request, queryset):
    paginator = PageNumberPagination()
    pagina = paginator.paginate_queryset(queryset, request)
    serializer = JustificacionInasistenciaSerializer(pagina, many=True)
    return paginator.get_paginated_response(serializer.data)


def _aplicar_filtros(request, queryset):
    estado = request.query_params.get("estado")
    if estado:
        if estado not in EstadoJustificacion.values:
            raise ValidationError({"estado": "El estado indicado no es valido."})
        queryset = queryset.filter(estado=estado)
    for parametro, campo in (
        ("asignacion_curso", "asistencia__asignacion_curso_id"),
        ("estudiante", "asistencia__matricula__estudiante_id"),
    ):
        valor = request.query_params.get(parametro)
        if valor is not None:
            try:
                valor = int(valor)
            except (TypeError, ValueError) as exc:
                raise ValidationError({parametro: "Debe ser un numero entero."}) from exc
            queryset = queryset.filter(**{campo: valor})
    return queryset


@extend_schema(parameters=FILTROS_JUSTIFICACIONES, responses=JustificacionInasistenciaSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsApoderado])
def justificaciones_apoderado(request):
    queryset = _aplicar_filtros(request, get_justificaciones_apoderado(request.user))
    return _respuesta_paginada(request, queryset)


@extend_schema(request=SolicitarCargaJustificacionSerializer, responses={201: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([IsApoderado])
def solicitar_carga(request):
    serializer = SolicitarCargaJustificacionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    justificacion, signed_url = solicitar_carga_justificacion(
        request.user,
        **serializer.validated_data,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="SOLICITAR_CARGA_JUSTIFICACION",
        modulo="asistencia",
        entidad="JustificacionInasistencia",
        entidad_id=str(justificacion.id),
    )
    return Response(
        {
            "justificacion": JustificacionInasistenciaSerializer(justificacion).data,
            "carga": {
                "url": signed_url,
                "metodo": "PUT",
                "headers": obtener_headers_carga(signed_url),
                "uso_inmediato": True,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(request=ConfirmarCargaSerializer, responses=JustificacionInasistenciaSerializer)
@api_view(["POST"])
@permission_classes([IsApoderado])
def confirmar_carga(request, justificacion_id):
    serializer = ConfirmarCargaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    justificacion = get_object_or_404(
        get_justificaciones_apoderado(request.user),
        pk=justificacion_id,
    )
    justificacion = confirmar_carga_justificacion(request.user, justificacion)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="CONFIRMAR_CARGA_JUSTIFICACION",
        modulo="asistencia",
        entidad="JustificacionInasistencia",
        entidad_id=str(justificacion.id),
    )
    return Response(JustificacionInasistenciaSerializer(justificacion).data)


@extend_schema(parameters=FILTROS_JUSTIFICACIONES, responses=JustificacionInasistenciaSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def justificaciones_docente(request):
    queryset = _aplicar_filtros(request, get_justificaciones_docente(request.user))
    return _respuesta_paginada(request, queryset)


@extend_schema(responses=JustificacionInasistenciaSerializer)
@api_view(["GET"])
@permission_classes([IsDocente])
def detalle_justificacion_docente(request, justificacion_id):
    justificacion = get_object_or_404(
        get_justificaciones_docente(request.user),
        pk=justificacion_id,
    )
    return Response(JustificacionInasistenciaSerializer(justificacion).data)


@extend_schema(request=RevisarJustificacionSerializer, responses=JustificacionInasistenciaSerializer)
@api_view(["PATCH"])
@permission_classes([IsDocente])
def revisar_justificacion_docente(request, justificacion_id):
    justificacion = get_object_or_404(
        get_justificaciones_docente(request.user),
        pk=justificacion_id,
    )
    serializer = RevisarJustificacionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    justificacion = revisar_justificacion(
        request.user,
        justificacion,
        **serializer.validated_data,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion=f"REVISAR_JUSTIFICACION_{justificacion.estado}",
        modulo="asistencia",
        entidad="JustificacionInasistencia",
        entidad_id=str(justificacion.id),
    )
    return Response(JustificacionInasistenciaSerializer(justificacion).data)


@extend_schema(parameters=FILTROS_JUSTIFICACIONES, responses=JustificacionInasistenciaSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def justificaciones_administracion(request):
    queryset = _aplicar_filtros(request, get_justificaciones_administracion())
    return _respuesta_paginada(request, queryset)


@extend_schema(parameters=FILTROS_JUSTIFICACIONES, responses=JustificacionInasistenciaSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsEstudiante])
def justificaciones_estudiante(request):
    queryset = _aplicar_filtros(request, get_justificaciones_estudiante(request.user))
    return _respuesta_paginada(request, queryset)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def descargar_justificacion(request, justificacion_id):
    justificacion = get_object_or_404(
        JustificacionInasistencia.objects.select_related(
            "archivo",
            "apoderado",
            "asistencia__matricula__estudiante",
            "asistencia__asignacion_curso__docente",
        ).exclude(estado=EstadoJustificacion.ELIMINADA),
        pk=justificacion_id,
    )
    signed_url = obtener_url_descarga_autorizada(request.user, justificacion)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="GENERAR_URL_DESCARGA_JUSTIFICACION",
        modulo="asistencia",
        entidad="JustificacionInasistencia",
        entidad_id=str(justificacion.id),
    )
    return Response({"url": signed_url, "uso_inmediato": True})


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["DELETE"])
@permission_classes([IsApoderado])
def retirar_justificacion(request, justificacion_id):
    justificacion = get_object_or_404(
        get_justificaciones_apoderado(request.user),
        pk=justificacion_id,
    )
    error_cloud = eliminar_justificacion(request.user, justificacion)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="ELIMINAR_LOGICO_JUSTIFICACION",
        modulo="asistencia",
        entidad="JustificacionInasistencia",
        entidad_id=str(justificacion.id),
    )
    return Response(
        {
            "detalle": "La justificacion fue retirada.",
            "limpieza_cloud_pendiente": error_cloud,
        }
    )
