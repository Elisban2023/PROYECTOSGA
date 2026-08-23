from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import EstadoRevisionIA, RegistroAuditoria
from sga.permissions import IsDocente
from sga.serializers import RecomendacionIARevisionSerializer, RecomendacionIASerializer
from sga.services.recomendaciones_docente import (
    generar_recomendacion_docente,
    get_recomendacion_docente,
    get_recomendaciones_docente,
    revisar_recomendacion_docente,
)


class GenerarRecomendacionSerializer(serializers.Serializer):
    matricula = serializers.IntegerField(min_value=1)
    asignacion_curso = serializers.IntegerField(min_value=1)
    periodo_academico = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
    )


FILTROS_RECOMENDACIONES = [
    OpenApiParameter("asignacion_curso", int, description="ID de la asignacion del docente."),
    OpenApiParameter("matricula", int, description="ID de la matricula."),
    OpenApiParameter("periodo_academico", int, description="ID del periodo academico."),
    OpenApiParameter(
        "estado_revision",
        str,
        enum=[choice for choice, _ in EstadoRevisionIA.choices],
    ),
]


def _entero_opcional(request, nombre):
    valor = request.query_params.get(nombre)
    if valor is None:
        return None
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        raise ValidationError({nombre: "Debe ser un numero entero."})
    if valor < 1:
        raise ValidationError({nombre: "Debe ser mayor o igual a 1."})
    return valor


@extend_schema(
    parameters=FILTROS_RECOMENDACIONES,
    responses=RecomendacionIASerializer(many=True),
)
@api_view(["GET"])
@permission_classes([IsDocente])
def recomendaciones_docente(request):
    estado_revision = request.query_params.get("estado_revision")
    if estado_revision and estado_revision not in EstadoRevisionIA.values:
        raise ValidationError(
            {"estado_revision": "El estado de revision no es valido."}
        )
    recomendaciones = get_recomendaciones_docente(
        request.user,
        asignacion_curso=_entero_opcional(request, "asignacion_curso"),
        matricula=_entero_opcional(request, "matricula"),
        periodo_academico=_entero_opcional(request, "periodo_academico"),
        estado_revision=estado_revision,
    )
    return Response(RecomendacionIASerializer(recomendaciones, many=True).data)


@extend_schema(responses=RecomendacionIASerializer)
@api_view(["GET"])
@permission_classes([IsDocente])
def detalle_recomendacion(request, recomendacion_id):
    recomendacion = get_recomendacion_docente(request.user, recomendacion_id)
    return Response(RecomendacionIASerializer(recomendacion).data)


@extend_schema(
    request=GenerarRecomendacionSerializer,
    responses={201: RecomendacionIASerializer},
)
@api_view(["POST"])
@permission_classes([IsDocente])
def generar_recomendacion(request):
    serializer = GenerarRecomendacionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    recomendacion = generar_recomendacion_docente(
        request.user,
        **serializer.validated_data,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="GENERAR_RECOMENDACION_IA",
        modulo="docente",
        entidad="RecomendacionIA",
        entidad_id=str(recomendacion.id),
    )
    return Response(
        RecomendacionIASerializer(recomendacion).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    request=RecomendacionIARevisionSerializer,
    responses=RecomendacionIASerializer,
)
@api_view(["PATCH"])
@permission_classes([IsDocente])
def revisar_recomendacion(request, recomendacion_id):
    serializer = RecomendacionIARevisionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    recomendacion = revisar_recomendacion_docente(
        request.user,
        recomendacion_id=recomendacion_id,
        **serializer.validated_data,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion=f"REVISAR_RECOMENDACION_{recomendacion.estado_revision}",
        modulo="docente",
        entidad="RecomendacionIA",
        entidad_id=str(recomendacion.id),
    )
    return Response(RecomendacionIASerializer(recomendacion).data)
