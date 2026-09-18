from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import RegistroAuditoria
from sga.permissions import IsAdminOrDirectivo, IsApoderado, IsDocente, IsEstudiante
from sga.roles import ROLE_APODERADO, ROLE_DOCENTE, ROLE_ESTUDIANTE
from sga.serializers.acciones_seguimiento import (
    AccionSeguimientoActualizarSerializer,
    AccionSeguimientoCrearSerializer,
    AccionSeguimientoSerializer,
    ActualizacionAccionCrearSerializer,
    ActualizacionAccionSeguimientoSerializer,
)
from sga.serializers.notificaciones import NotificacionSerializer
from sga.services.acciones_seguimiento import (
    acciones_base,
    actualizar_accion_docente,
    crear_accion_docente,
    crear_actualizacion,
    filtrar_acciones,
    get_accion_para_actualizar,
    get_acciones_apoderado,
    get_acciones_docente,
    get_acciones_estudiante,
)


FILTROS_ACCIONES = [
    OpenApiParameter("asignacion_curso", int),
    OpenApiParameter("matricula", int),
    OpenApiParameter("periodo_academico", int),
    OpenApiParameter("estado", str),
    OpenApiParameter("prioridad", str),
    OpenApiParameter("responsable", str),
    OpenApiParameter("vencidas", bool),
]


def _entero_query(request, nombre):
    valor = request.query_params.get(nombre)
    if valor in (None, ""):
        return None
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        raise ValidationError({nombre: "Debe ser un numero entero."})
    if valor < 1:
        raise ValidationError({nombre: "Debe ser mayor o igual a 1."})
    return valor


@extend_schema(
    parameters=FILTROS_ACCIONES,
    request=AccionSeguimientoCrearSerializer,
    responses={200: AccionSeguimientoSerializer(many=True), 201: OpenApiTypes.OBJECT},
)
@api_view(["GET", "POST"])
@permission_classes([IsDocente])
def acciones_seguimiento_docente(request):
    if request.method == "GET":
        queryset = filtrar_acciones(get_acciones_docente(request.user), request.query_params)
        return Response(AccionSeguimientoSerializer(queryset, many=True).data)

    serializer = AccionSeguimientoCrearSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    accion, notificaciones = crear_accion_docente(request.user, serializer.validated_data)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="CREAR_ACCION_SEGUIMIENTO",
        modulo="seguimiento",
        entidad="AccionSeguimiento",
        entidad_id=str(accion.id),
    )
    return Response(
        {
            "accion": AccionSeguimientoSerializer(accion).data,
            "notificaciones": NotificacionSerializer(notificaciones, many=True).data,
            "correos_enviados": sum(item.estado_envio == "ENVIADA" for item in notificaciones),
            "correos_fallidos": sum(item.estado_envio == "FALLIDA" for item in notificaciones),
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    request=AccionSeguimientoActualizarSerializer,
    responses=AccionSeguimientoSerializer,
)
@api_view(["GET", "PATCH"])
@permission_classes([IsDocente])
def accion_seguimiento_docente_detalle(request, accion_id):
    accion = get_accion_para_actualizar(request.user, accion_id, ROLE_DOCENTE)
    if request.method == "GET":
        return Response(AccionSeguimientoSerializer(accion).data)
    serializer = AccionSeguimientoActualizarSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    accion = actualizar_accion_docente(request.user, accion_id, serializer.validated_data)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion=f"ACTUALIZAR_ACCION_SEGUIMIENTO_{accion.estado}",
        modulo="seguimiento",
        entidad="AccionSeguimiento",
        entidad_id=str(accion.id),
    )
    return Response(AccionSeguimientoSerializer(accion).data)


@extend_schema(parameters=FILTROS_ACCIONES, responses=AccionSeguimientoSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsEstudiante])
def acciones_seguimiento_estudiante(request):
    queryset = filtrar_acciones(get_acciones_estudiante(request.user), request.query_params)
    return Response(AccionSeguimientoSerializer(queryset, many=True).data)


@extend_schema(
    parameters=FILTROS_ACCIONES + [OpenApiParameter("estudiante", int)],
    responses=AccionSeguimientoSerializer(many=True),
)
@api_view(["GET"])
@permission_classes([IsApoderado])
def acciones_seguimiento_apoderado(request):
    queryset = get_acciones_apoderado(
        request.user,
        estudiante_id=_entero_query(request, "estudiante"),
    )
    queryset = filtrar_acciones(queryset, request.query_params)
    return Response(AccionSeguimientoSerializer(queryset, many=True).data)


@extend_schema(
    parameters=FILTROS_ACCIONES + [OpenApiParameter("docente", int)],
    responses=AccionSeguimientoSerializer(many=True),
)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def acciones_seguimiento_administracion(request):
    queryset = filtrar_acciones(acciones_base(), request.query_params)
    return Response(AccionSeguimientoSerializer(queryset, many=True).data)


def _registrar_actualizacion(request, accion_id, rol):
    accion = get_accion_para_actualizar(request.user, accion_id, rol)
    serializer = ActualizacionAccionCrearSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    actualizacion = crear_actualizacion(
        request.user,
        accion,
        serializer.validated_data,
        rol=rol,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion=f"REGISTRAR_AVANCE_SEGUIMIENTO_{rol.upper()}",
        modulo="seguimiento",
        entidad="ActualizacionAccionSeguimiento",
        entidad_id=str(actualizacion.id),
    )
    return Response(
        ActualizacionAccionSeguimientoSerializer(actualizacion).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(request=ActualizacionAccionCrearSerializer, responses={201: ActualizacionAccionSeguimientoSerializer})
@api_view(["POST"])
@permission_classes([IsDocente])
def actualizar_progreso_docente(request, accion_id):
    return _registrar_actualizacion(request, accion_id, ROLE_DOCENTE)


@extend_schema(request=ActualizacionAccionCrearSerializer, responses={201: ActualizacionAccionSeguimientoSerializer})
@api_view(["POST"])
@permission_classes([IsEstudiante])
def actualizar_progreso_estudiante(request, accion_id):
    return _registrar_actualizacion(request, accion_id, ROLE_ESTUDIANTE)


@extend_schema(request=ActualizacionAccionCrearSerializer, responses={201: ActualizacionAccionSeguimientoSerializer})
@api_view(["POST"])
@permission_classes([IsApoderado])
def actualizar_progreso_apoderado(request, accion_id):
    return _registrar_actualizacion(request, accion_id, ROLE_APODERADO)
