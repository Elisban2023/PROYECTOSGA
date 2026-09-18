from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sga.serializers import DashboardFiltrosSerializer
from sga.services.dashboard import build_dashboard


@extend_schema(parameters=[DashboardFiltrosSerializer], responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    filtros = DashboardFiltrosSerializer(data=request.query_params)
    filtros.is_valid(raise_exception=True)
    return Response(build_dashboard(request.user, filtros.validated_data))
