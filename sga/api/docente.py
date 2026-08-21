from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from sga.models import (
    CriterioCalificacion,
    EstadoAcademico,
    EstadoMatricula,
    EstadoRegistro,
    Matricula,
    PeriodoAcademico,
)
from sga.permissions import IsDocente
from sga.serializers import (
    CriterioCalificacionSerializer,
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


@extend_schema(responses=CriterioCalificacionSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsDocente])
def criterios_mi_curso(request, asignacion_id):
    asignacion = get_object_or_404(
        get_asignaciones_docente(request.user),
        pk=asignacion_id,
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
