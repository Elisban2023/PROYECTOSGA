from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from sga.models import Asistencia, Calificacion, IncidenciaAcademica, ObservacionAcademica, Participacion
from sga.permissions import IsEstudiante
from sga.services.estudiante import get_matriculas_estudiante


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsEstudiante])
def mi_seguimiento(request):
    matriculas = get_matriculas_estudiante(request.user)
    resultado = []
    for matricula in matriculas:
        asistencias = Asistencia.objects.filter(matricula=matricula)
        total = asistencias.count()
        presentes = asistencias.filter(estado__in=("PRESENTE", "TARDE", "JUSTIFICADA")).count()
        resultado.append({
            "matricula_id": matricula.id,
            "anio_academico": matricula.anio_academico.anio,
            "grado_nombre": matricula.seccion.grado.nombre,
            "seccion_nombre": matricula.seccion.nombre,
            "asistencias": {"total": total, "presentes": presentes, "faltas": asistencias.filter(estado="FALTA").count(), "porcentaje": round(presentes * 100 / total, 2) if total else None},
            "calificaciones": list(Calificacion.objects.filter(matricula=matricula).values("valor").annotate(total=Count("id")).order_by("valor")),
            "participaciones": Participacion.objects.filter(matricula=matricula).count(),
            "observaciones": list(ObservacionAcademica.objects.filter(matricula=matricula, activo=True).order_by("-fecha").values("id", "fecha", "categoria", "descripcion")[:10]),
            "incidencias": list(IncidenciaAcademica.objects.filter(matricula=matricula).order_by("-fecha_registro").values("id", "tipo", "nivel", "estado", "descripcion", "fecha_registro")[:10]),
        })
    return Response(resultado)
