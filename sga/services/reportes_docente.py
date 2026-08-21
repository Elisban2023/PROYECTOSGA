from django.db.models import Count, Q
from rest_framework.exceptions import ValidationError

from sga.models import Asistencia, Calificacion, EstadoMatricula, Matricula, Participacion

from .docente import get_asignaciones_docente
from .seguimiento_docente import get_seguimiento_docente


def _asignaciones(user, asignacion_curso=None):
    queryset = get_asignaciones_docente(user)
    if asignacion_curso is not None:
        queryset = queryset.filter(pk=asignacion_curso)
        if not queryset.exists():
            raise ValidationError({"asignacion_curso": "No tiene una asignacion activa con ese identificador."})
    return queryset


def _ids(user, asignacion_curso=None):
    asignaciones = _asignaciones(user, asignacion_curso)
    return asignaciones, list(asignaciones.values_list("id", flat=True))


def build_reporte_docente_resumen(user, asignacion_curso=None):
    asignaciones, ids = _ids(user, asignacion_curso)
    secciones = set(asignaciones.values_list("seccion_id", "anio_academico_id"))
    matriculas = Matricula.objects.none()
    if secciones:
        condition = Q()
        for seccion_id, anio_id in secciones:
            condition |= Q(seccion_id=seccion_id, anio_academico_id=anio_id)
        matriculas = Matricula.objects.filter(condition, estado=EstadoMatricula.ACTIVA)
    asistencia = Asistencia.objects.filter(asignacion_curso_id__in=ids)
    return {
        "asignaciones": list(asignaciones.values("id", "curso__nombre", "seccion__nombre", "seccion__grado__nombre", "anio_academico__anio")),
        "estudiantes": matriculas.values("estudiante_id").distinct().count(),
        "asistencias": {
            "total": asistencia.count(),
            "presentes": asistencia.filter(estado__in=("PRESENTE", "TARDE", "JUSTIFICADA")).count(),
            "faltas": asistencia.filter(estado="FALTA").count(),
        },
        "calificaciones": Calificacion.objects.filter(asignacion_curso_id__in=ids).count(),
        "participaciones": Participacion.objects.filter(asignacion_curso_id__in=ids).count(),
    }


def build_reporte_docente_asistencias(user, asignacion_curso=None):
    _, ids = _ids(user, asignacion_curso)
    queryset = Asistencia.objects.filter(asignacion_curso_id__in=ids)
    return {
        "total": queryset.count(),
        "por_estado": list(queryset.values("estado").annotate(total=Count("id")).order_by("estado")),
        "por_curso": list(queryset.values("asignacion_curso_id", "asignacion_curso__curso__nombre", "asignacion_curso__seccion__nombre").annotate(total=Count("id"), faltas=Count("id", filter=Q(estado="FALTA"))).order_by("asignacion_curso__curso__nombre")),
    }


def build_reporte_docente_calificaciones(user, asignacion_curso=None):
    _, ids = _ids(user, asignacion_curso)
    queryset = Calificacion.objects.filter(asignacion_curso_id__in=ids)
    return {
        "total": queryset.count(),
        "por_nivel": list(queryset.values("valor").annotate(total=Count("id")).order_by("valor")),
        "por_criterio": list(queryset.values("criterio_calificacion_id", "criterio_calificacion__nombre").annotate(total=Count("id"), logro_destacado=Count("id", filter=Q(valor="AD")), logro_esperado=Count("id", filter=Q(valor="A")), en_proceso=Count("id", filter=Q(valor="B")), en_inicio=Count("id", filter=Q(valor="C"))).order_by("criterio_calificacion__nombre")),
    }


def build_reporte_docente_seguimiento(user, asignacion_curso=None):
    estudiantes = get_seguimiento_docente(user, asignacion_curso=asignacion_curso)
    return {
        "total": len(estudiantes),
        "con_faltas": sum(item["asistencias"]["faltas"] > 0 for item in estudiantes),
        "con_incidencias_abiertas": sum(item["incidencias_abiertas"] > 0 for item in estudiantes),
        "estudiantes": estudiantes,
    }
