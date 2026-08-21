from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.permissions import IsDocente
from sga.services.seguimiento_docente import get_detalle_seguimiento_docente, get_seguimiento_docente


def _asignacion_query_param(request):
    value = request.query_params.get("asignacion_curso")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({"asignacion_curso": "Debe ser un numero entero."})


@extend_schema(
    operation_id="listar_seguimiento_docente",
    responses=OpenApiTypes.OBJECT,
)
@api_view(["GET"])
@permission_classes([IsDocente])
def seguimiento_docente(request):
    return Response(get_seguimiento_docente(request.user, asignacion_curso=_asignacion_query_param(request)))


@extend_schema(
    operation_id="detalle_seguimiento_docente",
    responses=OpenApiTypes.OBJECT,
)
@api_view(["GET"])
@permission_classes([IsDocente])
def detalle_seguimiento_docente(request, matricula_id):
    return Response(get_detalle_seguimiento_docente(request.user, matricula_id=matricula_id, asignacion_curso=_asignacion_query_param(request)))
