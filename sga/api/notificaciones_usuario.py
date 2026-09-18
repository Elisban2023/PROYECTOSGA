from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from sga.models import PrioridadNotificacion, RegistroAuditoria, TipoNotificacion
from sga.permissions import IsDocente
from sga.roles import get_primary_role
from sga.serializers import (
    DestinatarioNotificacionSerializer,
    EnviarNotificacionSerializer,
    NotificacionEstadoSerializer,
    NotificacionSerializer,
)
from sga.services.notificaciones import (
    crear_notificaciones_docente,
    get_destinatarios_docente,
    get_notificaciones_enviadas_docente,
    get_notificaciones_usuario,
    marcar_como_leida,
    marcar_todas_como_leidas,
)


FILTROS_BANDEJA = [
    OpenApiParameter("solo_no_leidas", bool, description="Devuelve solo notificaciones pendientes de lectura."),
    OpenApiParameter("tipo", str, enum=TipoNotificacion.values),
    OpenApiParameter("prioridad", str, enum=PrioridadNotificacion.values),
    OpenApiParameter("desde_id", int, description="Devuelve novedades con ID mayor; util para polling."),
    OpenApiParameter("limite", int, description="Entre 1 y 100; por defecto 30."),
]


def _entero_query(request, nombre, default=None, minimo=1, maximo=None):
    valor = request.query_params.get(nombre)
    if valor in (None, ""):
        return default
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        from rest_framework.exceptions import ValidationError

        raise ValidationError({nombre: "Debe ser un numero entero."})
    if valor < minimo or (maximo is not None and valor > maximo):
        from rest_framework.exceptions import ValidationError

        raise ValidationError({nombre: f"Debe estar entre {minimo} y {maximo}."})
    return valor


@extend_schema(parameters=FILTROS_BANDEJA, responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mis_notificaciones_usuario(request):
    queryset = get_notificaciones_usuario(request.user)
    if request.query_params.get("solo_no_leidas", "").lower() in ("1", "true", "si"):
        queryset = queryset.filter(fecha_lectura__isnull=True)
    tipo = request.query_params.get("tipo")
    prioridad = request.query_params.get("prioridad")
    desde_id = _entero_query(request, "desde_id")
    limite = _entero_query(request, "limite", default=30, maximo=100)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if prioridad:
        queryset = queryset.filter(prioridad=prioridad)
    if desde_id:
        queryset = queryset.filter(id__gt=desde_id).order_by("id")

    resultados = list(queryset[:limite])
    base = get_notificaciones_usuario(request.user)
    return Response(
        {
            "results": NotificacionSerializer(resultados, many=True).data,
            "meta": {
                "no_leidas": base.filter(fecha_lectura__isnull=True).count(),
                "ultimo_id": base.order_by("-id").values_list("id", flat=True).first() or 0,
                "intervalo_polling_segundos": 20,
                "rol": get_primary_role(request.user),
            },
        }
    )


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def resumen_notificaciones_usuario(request):
    queryset = get_notificaciones_usuario(request.user)
    no_leidas = queryset.filter(fecha_lectura__isnull=True)
    return Response(
        {
            "total": queryset.count(),
            "no_leidas": no_leidas.count(),
            "urgentes_no_leidas": no_leidas.filter(prioridad=PrioridadNotificacion.URGENTE).count(),
            "altas_no_leidas": no_leidas.filter(prioridad=PrioridadNotificacion.ALTA).count(),
            "ultimo_id": queryset.order_by("-id").values_list("id", flat=True).first() or 0,
            "intervalo_polling_segundos": 20,
        }
    )


@extend_schema(request=None, responses=NotificacionEstadoSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def marcar_notificacion_usuario_leida(request, notificacion_id):
    notificacion = get_object_or_404(
        get_notificaciones_usuario(request.user), pk=notificacion_id
    )
    marcar_como_leida(notificacion)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="MARCAR_NOTIFICACION_LEIDA",
        modulo="notificaciones",
        entidad="Notificacion",
        entidad_id=str(notificacion.id),
    )
    return Response(NotificacionEstadoSerializer(notificacion).data)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def marcar_todas_notificaciones_leidas(request):
    actualizadas = marcar_todas_como_leidas(request.user)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="MARCAR_TODAS_NOTIFICACIONES_LEIDAS",
        modulo="notificaciones",
        entidad="Notificacion",
        entidad_id=None,
    )
    return Response({"actualizadas": actualizadas, "no_leidas": 0})


@extend_schema(
    parameters=[
        OpenApiParameter("rol", str, description="Rol por el que se desea filtrar."),
        OpenApiParameter("buscar", str, description="Nombre, usuario o DNI."),
        OpenApiParameter("incidencia_id", int, description="Limita al contexto de una incidencia del docente."),
    ],
    responses=DestinatarioNotificacionSerializer(many=True),
)
@api_view(["GET"])
@permission_classes([IsDocente])
def destinatarios_notificacion_docente(request):
    incidencia_id = _entero_query(request, "incidencia_id")
    usuarios = get_destinatarios_docente(
        request.user,
        rol=request.query_params.get("rol"),
        buscar=request.query_params.get("buscar"),
        incidencia_id=incidencia_id,
    )[:100]
    datos = [
        {
            "id": usuario.id,
            "nombre": usuario.get_full_name().strip() or usuario.username,
            "username": usuario.username,
            "rol": get_primary_role(usuario),
            "tiene_email": bool(usuario.email),
        }
        for usuario in usuarios
    ]
    return Response(DestinatarioNotificacionSerializer(datos, many=True).data)


@extend_schema(request=EnviarNotificacionSerializer, responses={201: OpenApiTypes.OBJECT})
@api_view(["POST"])
@permission_classes([IsDocente])
def enviar_notificacion_docente(request):
    serializer = EnviarNotificacionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    notificaciones = crear_notificaciones_docente(
        request.user,
        **serializer.validated_data,
    )
    for notificacion in notificaciones:
        RegistroAuditoria.registrar_evento(
            user=request.user,
            accion="ENVIAR_NOTIFICACION",
            modulo="docente",
            entidad="Notificacion",
            entidad_id=str(notificacion.id),
        )
    enviadas = sum(item.estado_envio == "ENVIADA" for item in notificaciones)
    fallidas = sum(item.estado_envio == "FALLIDA" for item in notificaciones)
    return Response(
        {
            "creadas": len(notificaciones),
            "correos_enviados": enviadas,
            "correos_fallidos": fallidas,
            "results": NotificacionSerializer(notificaciones, many=True).data,
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(responses=NotificacionSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def notificaciones_enviadas_docente(request):
    queryset = get_notificaciones_enviadas_docente(request.user)
    return Response(NotificacionSerializer(queryset[:100], many=True).data)
