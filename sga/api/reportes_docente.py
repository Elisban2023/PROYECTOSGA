from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.permissions import IsDocente
from sga.services.reportes_docente import (
    build_reporte_docente_asistencias,
    build_reporte_docente_calificaciones,
    build_reporte_docente_resumen,
    build_reporte_docente_seguimiento,
)


def _asignacion(request):
    value = request.query_params.get("asignacion_curso")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError({"asignacion_curso": "Debe ser un numero entero."})


def _response(builder, request):
    return Response(builder(request.user, _asignacion(request)))


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsDocente])
def reporte_docente_resumen(request):
    return _response(build_reporte_docente_resumen, request)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsDocente])
def reporte_docente_asistencias(request):
    return _response(build_reporte_docente_asistencias, request)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsDocente])
def reporte_docente_calificaciones(request):
    return _response(build_reporte_docente_calificaciones, request)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsDocente])
def reporte_docente_seguimiento(request):
    return _response(build_reporte_docente_seguimiento, request)
