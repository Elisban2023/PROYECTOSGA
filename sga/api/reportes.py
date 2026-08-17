from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from sga.permissions import IsAdminOrDirectivo
from sga.services.reportes import (
    build_reporte_academico,
    build_reporte_incidencias,
    build_reporte_matriculas,
    build_reporte_notificaciones,
    build_reporte_resumen,
)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def reporte_resumen(request):
    return Response(build_reporte_resumen())


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def reporte_matriculas(request):
    return Response(build_reporte_matriculas(request.query_params))


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def reporte_incidencias(request):
    return Response(build_reporte_incidencias(request.query_params))


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def reporte_notificaciones(request):
    return Response(build_reporte_notificaciones(request.query_params))


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def reporte_academico(request):
    return Response(build_reporte_academico(request.query_params))
