from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import Asistencia
from sga.permissions import IsApoderado
from sga.serializers.asistencia import AsistenciaDocenteSerializer
from sga.services.apoderado import get_vinculos_apoderado


@extend_schema(responses=AsistenciaDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsApoderado])
def asistencia_apoderado(request):
    estudiante_ids = get_vinculos_apoderado(request.user).values_list("estudiante_id", flat=True)
    queryset = Asistencia.objects.filter(matricula__estudiante_id__in=estudiante_ids).select_related(
        "matricula__estudiante__perfil__user", "asignacion_curso__curso", "asignacion_curso__seccion__grado"
    ).order_by("-fecha")
    for param, lookup in {"estudiante": "matricula__estudiante_id", "asignacion_curso": "asignacion_curso_id"}.items():
        value = request.query_params.get(param)
        if value is not None:
            try:
                queryset = queryset.filter(**{lookup: int(value)})
            except ValueError:
                raise ValidationError({param: "Debe ser un numero entero."})
    fecha = request.query_params.get("fecha")
    if fecha is not None:
        fecha_parseada = parse_date(fecha)
        if fecha_parseada is None:
            raise ValidationError({"fecha": "Use el formato YYYY-MM-DD."})
        queryset = queryset.filter(fecha=fecha_parseada)
    return Response(AsistenciaDocenteSerializer(queryset, many=True).data)
