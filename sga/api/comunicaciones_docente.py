from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from sga.models import RegistroAuditoria, TipoCorreo
from sga.permissions import IsDocente
from sga.serializers.comunicaciones_docente import ComunicacionDocenteSolicitudSerializer
from sga.serializers.correos import CorreoInstitucionalSerializer
from sga.services.comunicaciones_docente import (
    enviar_comunicacion_docente,
    get_comunicaciones_docente,
    previsualizar_comunicacion_docente,
)


FILTROS_COMUNICACIONES = [
    OpenApiParameter("tipo", str, enum=[valor for valor, _ in TipoCorreo.choices]),
    OpenApiParameter("matricula", int),
    OpenApiParameter("asignacion_curso", int),
    OpenApiParameter("estado", str, enum=["PENDIENTE", "ENVIADO", "FALLIDO"]),
]


@extend_schema(parameters=FILTROS_COMUNICACIONES, responses=CorreoInstitucionalSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def comunicaciones_docente(request):
    queryset = get_comunicaciones_docente(request.user)
    for parametro, campo in (
        ("tipo", "tipo"),
        ("matricula", "matricula_id"),
        ("asignacion_curso", "asignacion_curso_id"),
        ("estado", "estado"),
    ):
        valor = request.query_params.get(parametro)
        if valor:
            queryset = queryset.filter(**{campo: valor})
    paginador = PageNumberPagination()
    pagina = paginador.paginate_queryset(queryset, request)
    return paginador.get_paginated_response(CorreoInstitucionalSerializer(pagina, many=True).data)


@extend_schema(responses=CorreoInstitucionalSerializer)
@api_view(["GET"])
@permission_classes([IsDocente])
def detalle_comunicacion_docente(request, correo_id):
    correo = get_comunicaciones_docente(request.user).filter(pk=correo_id).first()
    if correo is None:
        raise NotFound("La comunicacion no existe o no fue enviada por este docente.")
    return Response(CorreoInstitucionalSerializer(correo).data)


@extend_schema(request=ComunicacionDocenteSolicitudSerializer, responses=OpenApiTypes.OBJECT)
@api_view(["POST"])
@permission_classes([IsDocente])
def previsualizar_comunicacion(request):
    serializer = ComunicacionDocenteSolicitudSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    comunicacion, contenido = previsualizar_comunicacion_docente(
        request.user,
        serializer.validated_data,
    )
    return Response(
        {
            "tipo": comunicacion["tipo"],
            "asunto": comunicacion["asunto"],
            "mensaje": comunicacion["mensaje"],
            "accion_texto": comunicacion["accion_texto"],
            "accion_url": comunicacion["accion_url"],
            "destinatarios": [
                {
                    "usuario_id": usuario.pk,
                    "nombre": usuario.get_full_name().strip() or usuario.username,
                    "email": usuario.email,
                }
                for usuario in comunicacion["destinatarios"]
            ],
            "omitidos": comunicacion["omitidos"],
            "texto": contenido["texto"],
            "html": contenido["html"],
        }
    )


@extend_schema(request=ComunicacionDocenteSolicitudSerializer, responses=OpenApiTypes.OBJECT)
@api_view(["POST"])
@permission_classes([IsDocente])
def enviar_comunicacion(request):
    serializer = ComunicacionDocenteSolicitudSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    comunicacion, enviados, fallidos = enviar_comunicacion_docente(
        request.user,
        serializer.validated_data,
    )
    for correo in enviados:
        RegistroAuditoria.registrar_evento(
            user=request.user,
            accion=f"ENVIAR_COMUNICACION_{correo.tipo}",
            modulo="docente",
            entidad="CorreoInstitucional",
            entidad_id=str(correo.pk),
        )
    for correo in fallidos:
        RegistroAuditoria.registrar_evento(
            user=request.user,
            accion=f"ENVIO_COMUNICACION_{correo.tipo}_FALLIDO",
            modulo="docente",
            entidad="CorreoInstitucional",
            entidad_id=str(correo.pk),
        )

    respuesta = {
        "detail": "Comunicacion procesada.",
        "enviados": CorreoInstitucionalSerializer(enviados, many=True).data,
        "fallidos": CorreoInstitucionalSerializer(fallidos, many=True).data,
        "omitidos": comunicacion["omitidos"],
    }
    if not enviados:
        respuesta["detail"] = "No se pudo enviar el correo a ningun apoderado."
        return Response(respuesta, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if fallidos:
        respuesta["detail"] = "La comunicacion se envio parcialmente."
        return Response(respuesta, status=status.HTTP_207_MULTI_STATUS)
    return Response(respuesta, status=status.HTTP_201_CREATED)
