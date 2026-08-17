from django.db.models import Count, Q

from sga.models import (
    Apoderado,
    AsignacionCurso,
    Curso,
    Docente,
    EstadoEnvio,
    EstadoIncidencia,
    EstadoMatricula,
    Estudiante,
    Grado,
    IncidenciaAcademica,
    Matricula,
    Notificacion,
    Seccion,
)


def build_reporte_resumen():
    return {
        "personas": {
            "estudiantes_activos": Estudiante.objects.filter(perfil__user__is_active=True).count(),
            "docentes_activos": Docente.objects.filter(perfil__user__is_active=True).count(),
            "apoderados_activos": Apoderado.objects.filter(perfil__user__is_active=True).count(),
        },
        "academico": {
            "grados_activos": Grado.objects.filter(activo=True).count(),
            "secciones_activas": Seccion.objects.filter(activo=True).count(),
            "cursos_activos": Curso.objects.filter(estado=True).count(),
            "asignaciones_activas": AsignacionCurso.objects.filter(estado="ACTIVO").count(),
            "matriculas_activas": Matricula.objects.filter(estado=EstadoMatricula.ACTIVA).count(),
        },
        "seguimiento": {
            "incidencias_abiertas": IncidenciaAcademica.objects.filter(estado=EstadoIncidencia.ABIERTA).count(),
            "incidencias_en_seguimiento": IncidenciaAcademica.objects.filter(estado=EstadoIncidencia.EN_SEGUIMIENTO).count(),
            "incidencias_cerradas": IncidenciaAcademica.objects.filter(estado=EstadoIncidencia.CERRADA).count(),
        },
        "notificaciones": _conteo_por_estado_envio(),
    }


def build_reporte_matriculas(params):
    queryset = _filtrar_matriculas(params)
    return {
        "total": queryset.count(),
        "por_estado": _values_count(queryset, "estado"),
        "por_anio": _values_count(queryset, "anio_academico__anio"),
        "por_grado": _values_count(queryset, "seccion__grado__nombre"),
        "por_seccion": list(
            queryset.values(
                "seccion_id",
                "seccion__nombre",
                "seccion__grado__nombre",
                "anio_academico__anio",
            )
            .annotate(total=Count("id"))
            .order_by("anio_academico__anio", "seccion__grado__nombre", "seccion__nombre")
        ),
    }


def build_reporte_incidencias(params):
    queryset = _filtrar_incidencias(params)
    return {
        "total": queryset.count(),
        "por_tipo": _values_count(queryset, "tipo"),
        "por_nivel": _values_count(queryset, "nivel"),
        "por_estado": _values_count(queryset, "estado"),
        "por_grado": _values_count(queryset, "matricula__seccion__grado__nombre"),
        "por_seccion": list(
            queryset.values(
                "matricula__seccion_id",
                "matricula__seccion__nombre",
                "matricula__seccion__grado__nombre",
                "matricula__anio_academico__anio",
            )
            .annotate(total=Count("id"))
            .order_by("matricula__anio_academico__anio", "matricula__seccion__grado__nombre", "matricula__seccion__nombre")
        ),
    }


def build_reporte_notificaciones(params):
    queryset = _filtrar_notificaciones(params)
    return {
        "total": queryset.count(),
        "por_estado_envio": _values_count(queryset, "estado_envio"),
        "por_estudiante": list(
            queryset.values(
                "incidencia__matricula__estudiante_id",
                "incidencia__matricula__estudiante__codigo_estudiante",
                "incidencia__matricula__estudiante__perfil__user__first_name",
                "incidencia__matricula__estudiante__perfil__user__last_name",
            )
            .annotate(total=Count("id"))
            .order_by("-total")[:20]
        ),
    }


def build_reporte_academico(params):
    asignaciones = _filtrar_asignaciones(params)
    matriculas = _filtrar_matriculas(params)
    return {
        "total_asignaciones": asignaciones.count(),
        "total_matriculas": matriculas.count(),
        "cursos_por_docente": list(
            asignaciones.values(
                "docente_id",
                "docente__perfil__user__first_name",
                "docente__perfil__user__last_name",
            )
            .annotate(total=Count("id"))
            .order_by("docente__perfil__user__last_name", "docente__perfil__user__first_name")
        ),
        "asignaciones_por_curso": list(
            asignaciones.values("curso_id", "curso__nombre")
            .annotate(total=Count("id"))
            .order_by("curso__nombre")
        ),
        "estudiantes_por_seccion": list(
            matriculas.filter(estado=EstadoMatricula.ACTIVA)
            .values(
                "seccion_id",
                "seccion__nombre",
                "seccion__grado__nombre",
                "anio_academico__anio",
            )
            .annotate(total=Count("estudiante_id", distinct=True))
            .order_by("anio_academico__anio", "seccion__grado__nombre", "seccion__nombre")
        ),
    }


def _conteo_por_estado_envio():
    data = {choice.value: 0 for choice in EstadoEnvio}
    data.update({item["estado_envio"]: item["total"] for item in Notificacion.objects.filter(activo=True).values("estado_envio").annotate(total=Count("id"))})
    return data


def _values_count(queryset, field):
    return list(queryset.values(field).annotate(total=Count("id")).order_by(field))


def _filtrar_matriculas(params):
    queryset = Matricula.objects.select_related("estudiante__perfil__user", "seccion__grado", "anio_academico")
    return _apply_filters(queryset, params, {
        "anio_academico": "anio_academico_id",
        "grado": "seccion__grado_id",
        "seccion": "seccion_id",
        "estado": "estado",
    })


def _filtrar_incidencias(params):
    queryset = IncidenciaAcademica.objects.select_related("matricula__seccion__grado", "matricula__anio_academico")
    return _apply_filters(queryset, params, {
        "anio_academico": "matricula__anio_academico_id",
        "grado": "matricula__seccion__grado_id",
        "seccion": "matricula__seccion_id",
        "tipo": "tipo",
        "nivel": "nivel",
        "estado": "estado",
    })


def _filtrar_notificaciones(params):
    queryset = Notificacion.objects.filter(activo=True).select_related(
        "incidencia__matricula__estudiante__perfil__user",
        "incidencia__matricula__seccion__grado",
        "apoderado__perfil__user",
    )
    return _apply_filters(queryset, params, {
        "anio_academico": "incidencia__matricula__anio_academico_id",
        "grado": "incidencia__matricula__seccion__grado_id",
        "seccion": "incidencia__matricula__seccion_id",
        "estado_envio": "estado_envio",
        "apoderado": "apoderado_id",
    })


def _filtrar_asignaciones(params):
    queryset = AsignacionCurso.objects.select_related("curso", "docente__perfil__user", "seccion__grado", "anio_academico")
    return _apply_filters(queryset, params, {
        "anio_academico": "anio_academico_id",
        "grado": "seccion__grado_id",
        "seccion": "seccion_id",
        "curso": "curso_id",
        "docente": "docente_id",
        "estado": "estado",
    })


def _apply_filters(queryset, params, filters_map):
    for param, field in filters_map.items():
        value = params.get(param)
        if value:
            queryset = queryset.filter(**{field: value})
    return queryset
