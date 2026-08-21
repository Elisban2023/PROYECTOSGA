from django.db.models import Count
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from sga.models import Asistencia, Calificacion, IncidenciaAcademica, ObservacionAcademica, Participacion
from sga.permissions import IsApoderado
from sga.services.apoderado import get_vinculos_apoderado


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsApoderado])
def seguimiento_apoderado(request):
    vinculos = get_vinculos_apoderado(request.user)
    estudiante_param = request.query_params.get("estudiante")
    if estudiante_param is not None:
        try:
            vinculos = vinculos.filter(estudiante_id=int(estudiante_param))
        except ValueError:
            raise ValidationError({"estudiante": "Debe ser un numero entero."})
    resultado = []
    for vinculo in vinculos:
        for matricula in vinculo.estudiante.matriculas.filter(estado="ACTIVA").select_related("seccion__grado", "anio_academico"):
            asistencias = Asistencia.objects.filter(matricula=matricula)
            total = asistencias.count()
            presentes = asistencias.filter(estado__in=("PRESENTE", "TARDE", "JUSTIFICADA")).count()
            resultado.append({
                "estudiante_id": vinculo.estudiante_id,
                "estudiante_nombre": vinculo.estudiante.perfil.user.get_full_name(),
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
