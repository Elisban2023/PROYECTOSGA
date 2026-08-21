from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import Calificacion
from sga.permissions import IsApoderado
from sga.serializers.calificaciones import CalificacionDocenteSerializer
from sga.services.apoderado import get_vinculos_apoderado


@extend_schema(responses=CalificacionDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsApoderado])
def calificaciones_apoderado(request):
    estudiante_ids = get_vinculos_apoderado(request.user).values_list("estudiante_id", flat=True)
    queryset = Calificacion.objects.filter(matricula__estudiante_id__in=estudiante_ids).select_related(
        "matricula__estudiante__perfil__user", "asignacion_curso__curso", "asignacion_curso__seccion",
        "periodo_academico", "criterio_calificacion__capacidad__competencia"
    ).order_by("-periodo_academico__fecha_inicio")
    for param, lookup in {"estudiante": "matricula__estudiante_id", "asignacion_curso": "asignacion_curso_id", "periodo_academico": "periodo_academico_id"}.items():
        value = request.query_params.get(param)
        if value is not None:
            try:
                queryset = queryset.filter(**{lookup: int(value)})
            except ValueError:
                raise ValidationError({param: "Debe ser un numero entero."})
    return Response(CalificacionDocenteSerializer(queryset, many=True).data)
