from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from sga.models import CorreoInstitucional, RegistroAuditoria
from sga.permissions import IsAdminOrDirectivo
from sga.serializers.correos import CorreoInstitucionalSerializer, CorreoSolicitudSerializer
from sga.services.correos import CorreoError, FORMATOS_ROL, enviar_correo_institucional, renderizar_correo


class CorreoInstitucionalViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAdminOrDirectivo,)
    serializer_class = CorreoInstitucionalSerializer
    queryset = CorreoInstitucional.objects.select_related("destinatario", "enviado_por")
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "asunto",
        "mensaje",
        "destinatario__username",
        "destinatario__first_name",
        "destinatario__last_name",
        "destinatario__email",
    )
    ordering_fields = ("fecha_creacion", "fecha_envio", "estado", "rol_destinatario")

    def get_queryset(self):
        queryset = super().get_queryset()
        for parametro, campo in (("rol", "rol_destinatario"), ("tipo", "tipo"), ("estado", "estado"), ("usuario", "destinatario_id")):
            valor = self.request.query_params.get(parametro)
            if valor:
                queryset = queryset.filter(**{campo: valor})
        return queryset

    @action(detail=False, methods=["get"], url_path="plantillas")
    def plantillas(self, request):
        return Response(
            [
                {
                    "rol": rol,
                    "encabezado": formato["encabezado"],
                    "descripcion": formato["descripcion"],
                }
                for rol, formato in FORMATOS_ROL.items()
            ]
        )

    @action(detail=False, methods=["post"], url_path="previsualizar")
    @extend_schema(request=CorreoSolicitudSerializer)
    def previsualizar(self, request):
        serializer = CorreoSolicitudSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        contenido = renderizar_correo(
            destinatario=datos["destinatario"],
            rol=datos["rol"],
            asunto=datos["asunto"],
            mensaje=datos["mensaje"],
            accion_texto=datos["accion_texto"],
            accion_url=datos["accion_url"],
        )
        return Response(
            {
                "rol": datos["rol"],
                "asunto": datos["asunto"],
                "texto": contenido["texto"],
                "html": contenido["html"],
            }
        )

    @action(detail=False, methods=["post"], url_path="enviar")
    @extend_schema(request=CorreoSolicitudSerializer, responses={201: CorreoInstitucionalSerializer})
    def enviar(self, request):
        serializer = CorreoSolicitudSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            correo = enviar_correo_institucional(enviado_por=request.user, **datos)
        except CorreoError as exc:
            correo = exc.correo
            RegistroAuditoria.registrar_evento(
                user=request.user,
                accion="ENVIO_CORREO_FALLIDO",
                modulo="correos",
                entidad="CorreoInstitucional",
                entidad_id=str(correo.pk) if correo else None,
            )
            return Response(
                {"detail": str(exc), "correo_id": correo.pk if correo else None},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        RegistroAuditoria.registrar_evento(
            user=request.user,
            accion="ENVIAR_CORREO",
            modulo="correos",
            entidad="CorreoInstitucional",
            entidad_id=str(correo.pk),
        )
        return Response(CorreoInstitucionalSerializer(correo).data, status=status.HTTP_201_CREATED)
