from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import RegistroAuditoria
from sga.permissions import IsDocente
from sga.serializers import (
    ActualizarCalificacionSerializer,
    CalificacionDocenteSerializer,
    RegistrarCalificacionesSerializer,
)
from sga.services.calificaciones import (
    get_calificaciones_docente,
    registrar_calificaciones_docente,
)


def _integer_query_param(request, name):
    value = request.query_params.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Debe ser un numero entero."})


@extend_schema(responses=CalificacionDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def calificaciones_docente(request):
    queryset = get_calificaciones_docente(request.user).order_by(
        "periodo_academico__fecha_inicio",
        "criterio_calificacion__nombre",
        "matricula__estudiante__perfil__user__last_name",
        "matricula__estudiante__perfil__user__first_name",
    )
    for param, lookup in {
        "asignacion_curso": "asignacion_curso_id",
        "periodo_academico": "periodo_academico_id",
        "criterio_calificacion": "criterio_calificacion_id",
        "matricula": "matricula_id",
    }.items():
        value = _integer_query_param(request, param)
        if value is not None:
            queryset = queryset.filter(**{lookup: value})
    return Response(CalificacionDocenteSerializer(queryset, many=True).data)


@extend_schema(
    request=RegistrarCalificacionesSerializer,
    responses=OpenApiTypes.OBJECT,
)
@api_view(["POST"])
@permission_classes([IsDocente])
def registrar_calificaciones(request):
    serializer = RegistrarCalificacionesSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    asignacion, periodo, criterio, calificaciones, creadas, actualizadas = (
        registrar_calificaciones_docente(
            request.user,
            **serializer.validated_data,
        )
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="REGISTRAR_CALIFICACIONES",
        modulo="docente",
        entidad="Calificacion",
        entidad_id=f"{asignacion.id}:{periodo.id}:{criterio.id}",
    )
    response_status = status.HTTP_201_CREATED if creadas else status.HTTP_200_OK
    return Response(
        {
            "creadas": creadas,
            "actualizadas": actualizadas,
            "registros": CalificacionDocenteSerializer(calificaciones, many=True).data,
        },
        status=response_status,
    )


@extend_schema(
    request=ActualizarCalificacionSerializer,
    responses=CalificacionDocenteSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsDocente])
def actualizar_calificacion(request, calificacion_id):
    calificacion = get_object_or_404(
        get_calificaciones_docente(request.user),
        pk=calificacion_id,
    )
    serializer = ActualizarCalificacionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    calificacion.valor = serializer.validated_data["valor"]
    calificacion.observacion = serializer.validated_data.get("observacion")
    calificacion.save(update_fields=["valor", "observacion"])
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="ACTUALIZAR_CALIFICACION",
        modulo="docente",
        entidad="Calificacion",
        entidad_id=str(calificacion.id),
    )
    return Response(CalificacionDocenteSerializer(calificacion).data)
