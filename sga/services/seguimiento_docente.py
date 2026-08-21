from collections import defaultdict

from django.db.models import Count, Q
from rest_framework.exceptions import ValidationError

from sga.models import (
    Asistencia,
    Calificacion,
    EstadoIncidencia,
    EstadoMatricula,
    IncidenciaAcademica,
    Matricula,
    ObservacionAcademica,
    Participacion,
)

from .docente import get_asignaciones_docente


def _contexto_docente(user, asignacion_curso=None):
    asignaciones = get_asignaciones_docente(user)
    if asignacion_curso is not None:
        asignaciones = asignaciones.filter(pk=asignacion_curso)
        if not asignaciones.exists():
            raise ValidationError({"asignacion_curso": "No tiene una asignacion activa con ese identificador."})
    docente_id = getattr(getattr(getattr(user, "perfil", None), "docente", None), "id", None)
    return docente_id, asignaciones


def _matriculas_de_asignaciones(asignaciones):
    seccion_anio = set(asignaciones.values_list("seccion_id", "anio_academico_id"))
    if not seccion_anio:
        return Matricula.objects.none()
    condition = Q()
    for seccion_id, anio_id in seccion_anio:
        condition |= Q(seccion_id=seccion_id, anio_academico_id=anio_id)
    return Matricula.objects.filter(condition, estado=EstadoMatricula.ACTIVA).select_related(
        "estudiante__perfil__user", "seccion__grado", "anio_academico"
    )


def _counts(queryset, **aggregates):
    return {row["matricula_id"]: row for row in queryset.values("matricula_id").annotate(**aggregates)}


def _resumenes(user, asignacion_curso=None):
    docente_id, asignaciones = _contexto_docente(user, asignacion_curso)
    matriculas = list(_matriculas_de_asignaciones(asignaciones))
    matricula_ids = [matricula.id for matricula in matriculas]
    asignacion_ids = list(asignaciones.values_list("id", flat=True))
    if not matricula_ids:
        return [], asignacion_ids
    asistencias = _counts(
        Asistencia.objects.filter(matricula_id__in=matricula_ids, asignacion_curso_id__in=asignacion_ids),
        total=Count("id"),
        presentes=Count("id", filter=Q(estado__in=("PRESENTE", "TARDE", "JUSTIFICADA"))),
        faltas=Count("id", filter=Q(estado="FALTA")),
    )
    calificaciones = defaultdict(lambda: {"total": 0, "AD": 0, "A": 0, "B": 0, "C": 0})
    for row in Calificacion.objects.filter(matricula_id__in=matricula_ids, asignacion_curso_id__in=asignacion_ids).values("matricula_id", "valor"):
        calificaciones[row["matricula_id"]]["total"] += 1
        if row["valor"] in calificaciones[row["matricula_id"]]:
            calificaciones[row["matricula_id"]][row["valor"]] += 1
    participaciones = _counts(
        Participacion.objects.filter(matricula_id__in=matricula_ids, asignacion_curso_id__in=asignacion_ids), total=Count("id")
    )
    observaciones = _counts(
        ObservacionAcademica.objects.filter(matricula_id__in=matricula_ids, asignacion_curso_id__in=asignacion_ids, docente_id=docente_id, activo=True), total=Count("id")
    )
    incidencias = _counts(
        IncidenciaAcademica.objects.filter(matricula_id__in=matricula_ids, observacion__asignacion_curso_id__in=asignacion_ids, observacion__docente_id=docente_id, estado__in=(EstadoIncidencia.ABIERTA, EstadoIncidencia.EN_SEGUIMIENTO)), total=Count("id")
    )
    resultado = []
    for matricula in matriculas:
        asistencia = asistencias.get(matricula.id, {"total": 0, "presentes": 0, "faltas": 0})
        total = asistencia["total"]
        resultado.append({
            "matricula_id": matricula.id,
            "estudiante_id": matricula.estudiante_id,
            "estudiante_codigo": matricula.estudiante.codigo_estudiante,
            "estudiante_nombre": matricula.estudiante.perfil.user.get_full_name(),
            "grado_nombre": matricula.seccion.grado.nombre,
            "seccion_nombre": matricula.seccion.nombre,
            "anio_academico": matricula.anio_academico.anio,
            "asistencias": {"total": total, "presentes": asistencia["presentes"], "faltas": asistencia["faltas"], "porcentaje": round(asistencia["presentes"] * 100 / total, 2) if total else None},
            "calificaciones": calificaciones[matricula.id],
            "participaciones": participaciones.get(matricula.id, {"total": 0})["total"],
            "observaciones": observaciones.get(matricula.id, {"total": 0})["total"],
            "incidencias_abiertas": incidencias.get(matricula.id, {"total": 0})["total"],
        })
    return resultado, asignacion_ids


def get_seguimiento_docente(user, *, asignacion_curso=None):
    resumenes, _ = _resumenes(user, asignacion_curso)
    return resumenes


def get_detalle_seguimiento_docente(user, *, matricula_id, asignacion_curso=None):
    resumenes, asignacion_ids = _resumenes(user, asignacion_curso)
    resultado = next((item for item in resumenes if item["matricula_id"] == matricula_id), None)
    if resultado is None:
        raise ValidationError({"matricula": "No tiene acceso a esa matricula desde sus cursos activos."})
    docente_id = user.perfil.docente.id
    resultado["ultimas_asistencias"] = list(Asistencia.objects.filter(matricula_id=matricula_id, asignacion_curso_id__in=asignacion_ids).order_by("-fecha").values("id", "fecha", "estado", "justificacion")[:10])
    resultado["ultimas_calificaciones"] = list(Calificacion.objects.filter(matricula_id=matricula_id, asignacion_curso_id__in=asignacion_ids).order_by("-id").values("id", "valor", "observacion", "periodo_academico__nombre", "criterio_calificacion__nombre")[:10])
    resultado["ultimas_participaciones"] = list(Participacion.objects.filter(matricula_id=matricula_id, asignacion_curso_id__in=asignacion_ids).order_by("-fecha").values("id", "fecha", "tipo", "valor", "observacion")[:10])
    resultado["ultimas_observaciones"] = list(ObservacionAcademica.objects.filter(matricula_id=matricula_id, asignacion_curso_id__in=asignacion_ids, docente_id=docente_id, activo=True).order_by("-fecha").values("id", "fecha", "categoria", "descripcion")[:10])
    resultado["incidencias_abiertas_detalle"] = list(IncidenciaAcademica.objects.filter(matricula_id=matricula_id, observacion__asignacion_curso_id__in=asignacion_ids, observacion__docente_id=docente_id, estado__in=(EstadoIncidencia.ABIERTA, EstadoIncidencia.EN_SEGUIMIENTO)).order_by("-fecha_registro").values("id", "tipo", "nivel", "estado", "descripcion", "fecha_registro")[:10])
    return resultado
