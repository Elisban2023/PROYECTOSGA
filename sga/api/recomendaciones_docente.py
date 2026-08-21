from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import serializers, status

from sga.permissions import IsDocente
from sga.serializers import RecomendacionIASerializer
from sga.services.recomendaciones_docente import generar_recomendacion_docente, get_recomendaciones_docente


class GenerarRecomendacionSerializer(serializers.Serializer):
    matricula = serializers.IntegerField(min_value=1)
    asignacion_curso = serializers.IntegerField(min_value=1)
    periodo_academico = serializers.IntegerField(min_value=1, required=False, allow_null=True)


@extend_schema(responses=RecomendacionIASerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def recomendaciones_docente(request):
    return Response(RecomendacionIASerializer(get_recomendaciones_docente(request.user), many=True).data)


@extend_schema(request=GenerarRecomendacionSerializer, responses=RecomendacionIASerializer)
@api_view(["POST"])
@permission_classes([IsDocente])
def generar_recomendacion(request):
    serializer = GenerarRecomendacionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    recomendacion = generar_recomendacion_docente(request.user, **serializer.validated_data)
    return Response(RecomendacionIASerializer(recomendacion).data, status=status.HTTP_201_CREATED)
