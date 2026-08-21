from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import Calificacion
from sga.permissions import IsEstudiante
from sga.serializers.calificaciones import CalificacionDocenteSerializer
from sga.services.estudiante import get_matriculas_estudiante


@extend_schema(responses=CalificacionDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsEstudiante])
def mis_calificaciones(request):
    matricula_ids = [matricula.id for matricula in get_matriculas_estudiante(request.user)]
    queryset = Calificacion.objects.filter(matricula_id__in=matricula_ids).select_related(
        "matricula__estudiante__perfil__user", "asignacion_curso__curso", "asignacion_curso__seccion",
        "periodo_academico", "criterio_calificacion__capacidad__competencia"
    ).order_by("-periodo_academico__fecha_inicio", "asignacion_curso__curso__nombre")
    for param, lookup in {
        "asignacion_curso": "asignacion_curso_id",
        "periodo_academico": "periodo_academico_id",
        "criterio_calificacion": "criterio_calificacion_id",
    }.items():
        value = request.query_params.get(param)
        if value is not None:
            try:
                queryset = queryset.filter(**{lookup: int(value)})
            except ValueError:
                raise ValidationError({param: "Debe ser un numero entero."})
    return Response(CalificacionDocenteSerializer(queryset, many=True).data)
