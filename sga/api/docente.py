from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import (
    Capacidad,
    CriterioCalificacion,
    EstadoAcademico,
    EstadoMatricula,
    EstadoRegistro,
    Matricula,
    PeriodoAcademico,
    RegistroAuditoria,
)
from sga.permissions import IsDocente
from sga.serializers import (
    CapacidadSerializer,
    CriterioCalificacionSerializer,
    CrearCriterioDocenteSerializer,
    DocenteCursoSerializer,
    DocenteEstudianteCursoSerializer,
    PeriodoAcademicoSerializer,
)
from sga.services.docente import get_asignaciones_docente


@extend_schema(responses=DocenteCursoSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def mis_cursos(request):
    serializer = DocenteCursoSerializer(get_asignaciones_docente(request.user), many=True)
    return Response(serializer.data)


@extend_schema(responses=DocenteEstudianteCursoSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def estudiantes_mi_curso(request, asignacion_id):
    asignacion = get_object_or_404(
        get_asignaciones_docente(request.user),
        pk=asignacion_id,
    )
    matriculas = (
        Matricula.objects.filter(
            seccion_id=asignacion.seccion_id,
            anio_academico_id=asignacion.anio_academico_id,
            estado=EstadoMatricula.ACTIVA,
        )
        .select_related("estudiante__perfil__user")
        .order_by(
            "estudiante__perfil__user__last_name",
            "estudiante__perfil__user__first_name",
            "estudiante__codigo_estudiante",
        )
    )
    serializer = DocenteEstudianteCursoSerializer(matriculas, many=True)
    return Response(serializer.data)


@extend_schema(responses=PeriodoAcademicoSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def periodos_mi_curso(request, asignacion_id):
    asignacion = get_object_or_404(
        get_asignaciones_docente(request.user),
        pk=asignacion_id,
    )
    periodos = PeriodoAcademico.objects.filter(
        anio_academico_id=asignacion.anio_academico_id,
        estado__in=(
            EstadoAcademico.PLANIFICADO,
            EstadoAcademico.ACTIVO,
            EstadoAcademico.CERRADO,
        ),
    ).order_by("fecha_inicio", "nombre")
    return Response(PeriodoAcademicoSerializer(periodos, many=True).data)


@extend_schema(
    methods=["GET"],
    responses=CriterioCalificacionSerializer(many=True),
)
@extend_schema(
    methods=["POST"],
    request=CrearCriterioDocenteSerializer,
    responses={201: CriterioCalificacionSerializer},
)
@api_view(["GET", "POST"])
@permission_classes([IsDocente])
def criterios_mi_curso(request, asignacion_id):
    asignacion = get_object_or_404(
        get_asignaciones_docente(request.user),
        pk=asignacion_id,
    )
    if request.method == "POST":
        serializer = CrearCriterioDocenteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        capacidad = serializer.validated_data["capacidad"]
        if capacidad.competencia.curso_id != asignacion.curso_id:
            raise ValidationError(
                {"capacidad": "La capacidad debe pertenecer al curso asignado."}
            )
        nombre = serializer.validated_data["nombre"]
        if CriterioCalificacion.objects.filter(
            capacidad=capacidad,
            nombre__iexact=nombre,
        ).exists():
            raise ValidationError(
                {"nombre": "Ya existe un criterio con este nombre para la capacidad."}
            )
        try:
            with transaction.atomic():
                criterio = serializer.save(estado=EstadoRegistro.ACTIVO)
        except IntegrityError as exc:
            raise ValidationError(
                {"nombre": "Ya existe un criterio con este nombre para la capacidad."}
            ) from exc
        RegistroAuditoria.registrar_evento(
            user=request.user,
            accion="CREAR_CRITERIO_CALIFICACION",
            modulo="docente",
            entidad="CriterioCalificacion",
            entidad_id=str(criterio.id),
        )
        return Response(
            CriterioCalificacionSerializer(criterio).data,
            status=status.HTTP_201_CREATED,
        )

    criterios = CriterioCalificacion.objects.filter(
        capacidad__competencia__curso_id=asignacion.curso_id,
        estado=EstadoRegistro.ACTIVO,
        capacidad__estado=EstadoRegistro.ACTIVO,
        capacidad__competencia__estado=EstadoRegistro.ACTIVO,
        capacidad__competencia__curso__estado=EstadoRegistro.ACTIVO,
    ).select_related(
        "capacidad__competencia__curso"
    ).order_by(
        "capacidad__competencia__nombre",
        "capacidad__nombre",
        "nombre",
    )
    return Response(CriterioCalificacionSerializer(criterios, many=True).data)


@extend_schema(responses=CapacidadSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def capacidades_mi_curso(request, asignacion_id):
    asignacion = get_object_or_404(
        get_asignaciones_docente(request.user),
        pk=asignacion_id,
    )
    capacidades = Capacidad.objects.filter(
        competencia__curso_id=asignacion.curso_id,
        estado=EstadoRegistro.ACTIVO,
        competencia__estado=EstadoRegistro.ACTIVO,
        competencia__curso__estado=EstadoRegistro.ACTIVO,
    ).select_related(
        "competencia__curso"
    ).order_by(
        "competencia__nombre",
        "nombre",
    )
    return Response(CapacidadSerializer(capacidades, many=True).data)
