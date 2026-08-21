from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from sga.permissions import IsEstudiante
from sga.serializers.estudiante import EstudianteCursoSerializer
from sga.services.estudiante import get_asignaciones_estudiante


@extend_schema(responses=EstudianteCursoSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsEstudiante])
def mis_cursos_estudiante(request):
    return Response(EstudianteCursoSerializer(get_asignaciones_estudiante(request.user), many=True).data)
