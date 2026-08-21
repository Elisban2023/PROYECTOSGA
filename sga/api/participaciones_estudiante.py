from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import Participacion
from sga.permissions import IsEstudiante
from sga.serializers.participaciones import ParticipacionDocenteSerializer
from sga.services.estudiante import get_matriculas_estudiante


@extend_schema(responses=ParticipacionDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsEstudiante])
def mi_participacion(request):
    matricula_ids = [matricula.id for matricula in get_matriculas_estudiante(request.user)]
    queryset = Participacion.objects.filter(matricula_id__in=matricula_ids).select_related(
        "matricula__estudiante__perfil__user", "asignacion_curso__curso", "asignacion_curso__seccion", "periodo_academico"
    ).order_by("-fecha")
    for param, lookup in {"asignacion_curso": "asignacion_curso_id", "periodo_academico": "periodo_academico_id"}.items():
        value = request.query_params.get(param)
        if value is not None:
            try:
                queryset = queryset.filter(**{lookup: int(value)})
            except ValueError:
                raise ValidationError({param: "Debe ser un numero entero."})
    tipo = request.query_params.get("tipo")
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    return Response(ParticipacionDocenteSerializer(queryset, many=True).data)
