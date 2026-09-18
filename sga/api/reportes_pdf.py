import re

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from sga.models import RegistroAuditoria
from sga.serializers.reportes_pdf import ReportePDFQuerySerializer
from sga.services.reportes_pdf import construir_reporte_pdf


@extend_schema(
    parameters=[ReportePDFQuerySerializer],
    responses={(200, "application/pdf"): OpenApiTypes.BINARY},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exportar_reporte_pdf(request):
    serializer = ReportePDFQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    pdf, titulo = construir_reporte_pdf(request.user, serializer.validated_data)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion=f"EXPORTAR_REPORTE_PDF_{serializer.validated_data['tipo'].upper()}",
        modulo="reportes",
        entidad="ReportePDF",
    )
    nombre = re.sub(r"[^a-z0-9]+", "-", titulo.lower()).strip("-")
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nombre}.pdf"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    response["Pragma"] = "no-cache"
    return response
