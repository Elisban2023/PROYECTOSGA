from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import Asistencia
from sga.permissions import IsEstudiante
from sga.serializers.asistencia import AsistenciaDocenteSerializer
from sga.services.estudiante import get_matriculas_estudiante


@extend_schema(responses=AsistenciaDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsEstudiante])
def mi_asistencia(request):
    matricula_ids = [matricula.id for matricula in get_matriculas_estudiante(request.user)]
    queryset = Asistencia.objects.filter(matricula_id__in=matricula_ids).select_related(
        "matricula__estudiante__perfil__user", "asignacion_curso__curso", "asignacion_curso__seccion__grado"
    ).order_by("-fecha", "asignacion_curso__curso__nombre")
    for param, lookup in {"asignacion_curso": "asignacion_curso_id", "anio_academico": "asignacion_curso__anio_academico_id"}.items():
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
