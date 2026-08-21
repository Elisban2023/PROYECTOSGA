from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import RegistroAuditoria
from sga.permissions import IsDocente
from sga.serializers import (
    ActualizarParticipacionSerializer,
    ParticipacionDocenteSerializer,
    RegistrarParticipacionSerializer,
)
from sga.services.participaciones import (
    actualizar_participacion_docente,
    get_participaciones_docente,
    registrar_participacion_docente,
)


def _integer_query_param(request, name):
    value = request.query_params.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Debe ser un numero entero."})


@extend_schema(responses=ParticipacionDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def participaciones_docente(request):
    queryset = get_participaciones_docente(request.user).order_by(
        "-fecha",
        "matricula__estudiante__perfil__user__last_name",
        "matricula__estudiante__perfil__user__first_name",
    )
    for param, lookup in {
        "asignacion_curso": "asignacion_curso_id",
        "matricula": "matricula_id",
        "periodo_academico": "periodo_academico_id",
    }.items():
        value = _integer_query_param(request, param)
        if value is not None:
            queryset = queryset.filter(**{lookup: value})

    tipo = request.query_params.get("tipo")
    if tipo is not None:
        queryset = queryset.filter(tipo=tipo)

    fecha = request.query_params.get("fecha")
    if fecha is not None:
        fecha_parseada = parse_date(fecha)
        if fecha_parseada is None:
            raise ValidationError({"fecha": "Use el formato YYYY-MM-DD."})
        queryset = queryset.filter(fecha__date=fecha_parseada)
    return Response(ParticipacionDocenteSerializer(queryset, many=True).data)


@extend_schema(
    request=RegistrarParticipacionSerializer,
    responses=ParticipacionDocenteSerializer,
)
@api_view(["POST"])
@permission_classes([IsDocente])
def registrar_participacion(request):
    serializer = RegistrarParticipacionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    participacion = registrar_participacion_docente(
        request.user,
        **serializer.validated_data,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="REGISTRAR_PARTICIPACION",
        modulo="docente",
        entidad="Participacion",
        entidad_id=str(participacion.id),
    )
    return Response(
        ParticipacionDocenteSerializer(participacion).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    request=ActualizarParticipacionSerializer,
    responses=ParticipacionDocenteSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsDocente])
def actualizar_participacion(request, participacion_id):
    participacion = get_object_or_404(
        get_participaciones_docente(request.user),
        pk=participacion_id,
    )
    serializer = ActualizarParticipacionSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    if not serializer.validated_data:
        raise ValidationError("Envie al menos un campo para actualizar.")
    participacion = actualizar_participacion_docente(
        request.user,
        participacion,
        **serializer.validated_data,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="ACTUALIZAR_PARTICIPACION",
        modulo="docente",
        entidad="Participacion",
        entidad_id=str(participacion.id),
    )
    return Response(ParticipacionDocenteSerializer(participacion).data)
