from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import RegistroAuditoria
from sga.permissions import IsDocente
from sga.serializers import (
    ActualizarObservacionDocenteSerializer,
    ObservacionDocenteSerializer,
    RegistrarObservacionDocenteSerializer,
)
from sga.services.observaciones_docente import (
    actualizar_observacion_docente,
    get_observaciones_docente,
    registrar_observacion_docente,
)


def _integer_query_param(request, name):
    value = request.query_params.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Debe ser un numero entero."})


@extend_schema(responses=ObservacionDocenteSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def observaciones_docente(request):
    queryset = get_observaciones_docente(request.user).order_by("-fecha")
    for param, lookup in {
        "asignacion_curso": "asignacion_curso_id",
        "matricula": "matricula_id",
    }.items():
        value = _integer_query_param(request, param)
        if value is not None:
            queryset = queryset.filter(**{lookup: value})

    categoria = request.query_params.get("categoria")
    if categoria:
        queryset = queryset.filter(categoria__iexact=categoria.strip())
    fecha = request.query_params.get("fecha")
    if fecha is not None:
        fecha_parseada = parse_date(fecha)
        if fecha_parseada is None:
            raise ValidationError({"fecha": "Use el formato YYYY-MM-DD."})
        queryset = queryset.filter(fecha__date=fecha_parseada)
    if request.query_params.get("incluir_inactivas") != "true":
        queryset = queryset.filter(activo=True)
    return Response(ObservacionDocenteSerializer(queryset, many=True).data)


@extend_schema(
    request=RegistrarObservacionDocenteSerializer,
    responses=ObservacionDocenteSerializer,
)
@api_view(["POST"])
@permission_classes([IsDocente])
def registrar_observacion(request):
    serializer = RegistrarObservacionDocenteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    observacion = registrar_observacion_docente(request.user, **serializer.validated_data)
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="REGISTRAR_OBSERVACION",
        modulo="docente",
        entidad="ObservacionAcademica",
        entidad_id=str(observacion.id),
    )
    return Response(
        ObservacionDocenteSerializer(observacion).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    request=ActualizarObservacionDocenteSerializer,
    responses=ObservacionDocenteSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsDocente])
def actualizar_observacion(request, observacion_id):
    observacion = get_object_or_404(
        get_observaciones_docente(request.user).filter(activo=True),
        pk=observacion_id,
    )
    serializer = ActualizarObservacionDocenteSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    if not serializer.validated_data:
        raise ValidationError("Envie al menos un campo para actualizar.")
    observacion = actualizar_observacion_docente(
        request.user,
        observacion,
        **serializer.validated_data,
    )
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="ACTUALIZAR_OBSERVACION",
        modulo="docente",
        entidad="ObservacionAcademica",
        entidad_id=str(observacion.id),
    )
    return Response(ObservacionDocenteSerializer(observacion).data)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["DELETE"])
@permission_classes([IsDocente])
def eliminar_observacion(request, observacion_id):
    observacion = get_object_or_404(
        get_observaciones_docente(request.user).filter(activo=True),
        pk=observacion_id,
    )
    observacion.activo = False
    observacion.save(update_fields=["activo"])
    RegistroAuditoria.registrar_evento(
        user=request.user,
        accion="DESACTIVAR_OBSERVACION",
        modulo="docente",
        entidad="ObservacionAcademica",
        entidad_id=str(observacion.id),
    )
    return Response({"detail": "Observacion desactivada correctamente."})
