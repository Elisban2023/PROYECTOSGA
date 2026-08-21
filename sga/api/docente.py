from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from sga.models import EstadoMatricula, Matricula
from sga.permissions import IsDocente
from sga.serializers import (
    DocenteCursoSerializer,
    DocenteEstudianteCursoSerializer,
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
