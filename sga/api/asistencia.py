from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import RegistroAuditoria
from sga.permissions import IsDocente
from sga.serializers import (
    ActualizarAsistenciaSerializer,
    AsistenciaDocenteSerializer,
    RegistrarAsistenciasSerializer,
)
from sga.services.asistencia import (
    get_asistencias_docente,
    registrar_asistencias_docente,
)


def _integer_query_param(request, name):
    value = request.query_params.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Debe ser un numero entero."})


@extend_schema(responses=AsistenciaDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def asistencias_docente(request):
    queryset = get_asistencias_docente(request.user).order_by(
        "-fecha",
        "matricula__estudiante__perfil__user__last_name",
        "matricula__estudiante__perfil__user__first_name",
    )
    for param, lookup in {
        "asignacion_curso": "asignacion_curso_id",
        "matricula": "matricula_id",
    }.items():
        value = _integer_query_param(request, param)
        if value is not None:
            queryset = queryset.filter(**{lookup: value})

    fecha = request.query_params.get("fecha")
    if fecha is not None:
        fecha_parseada = parse_date(fecha)
        if fecha_parseada is None:
            raise ValidationError({"fecha": "Use el formato YYYY-MM-DD."})
        queryset = queryset.filter(fecha=fecha_parseada)

    serializer = AsistenciaDocenteSerializer(queryset, many=True)
    return Response(serializer.data)


@extend_schema(
    request=RegistrarAsistenciasSerializer,
    responses=OpenApiTypes.OBJECT,
)
@api_view(["POST"])
@permission_classes([IsDocente])
def registrar_asistencias(request):
    serializer = RegistrarAsistenciasSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    asignacion, asistencias, creados, actualizados = registrar_asistencias_docente(
        request.user,
        **serializer.validated_data,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="REGISTRAR_ASISTENCIAS",
        modulo="docente",
        entidad="Asistencia",
        entidad_id=f"{asignacion.id}:{serializer.validated_data['fecha'].isoformat()}",
    )
    response_serializer = AsistenciaDocenteSerializer(
        asistencias,
        many=True,
        context={"request": request},
    )
    response_status = status.HTTP_201_CREATED if creados else status.HTTP_200_OK
    return Response(
        {
            "creados": creados,
            "actualizados": actualizados,
            "registros": response_serializer.data,
        },
        status=response_status,
    )


@extend_schema(
    request=ActualizarAsistenciaSerializer,
    responses=AsistenciaDocenteSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsDocente])
def actualizar_asistencia(request, asistencia_id):
    asistencia = get_object_or_404(
        get_asistencias_docente(request.user),
        pk=asistencia_id,
    )
    serializer = ActualizarAsistenciaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    asistencia.estado = serializer.validated_data["estado"]
    asistencia.justificacion = serializer.validated_data.get("justificacion")
    asistencia.save(update_fields=["estado", "justificacion"])
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="ACTUALIZAR_ASISTENCIA",
        modulo="docente",
        entidad="Asistencia",
        entidad_id=str(asistencia.id),
    )
    return Response(AsistenciaDocenteSerializer(asistencia).data)
