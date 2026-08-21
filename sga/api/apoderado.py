from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from sga.permissions import IsApoderado
from sga.serializers.apoderado import ApoderadoEstudianteSerializer
from sga.services.apoderado import get_vinculos_apoderado


@extend_schema(responses=ApoderadoEstudianteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsApoderado])
def mis_estudiantes_apoderado(request):
    return Response(ApoderadoEstudianteSerializer(get_vinculos_apoderado(request.user), many=True).data)
