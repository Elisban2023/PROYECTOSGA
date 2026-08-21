from django.db.models import Count, Q

from sga.models import (
    Apoderado,
    AsignacionCurso,
    Asistencia,
    Calificacion,
    Docente,
    EstadoEnvio,
    EstadoGeneral,
    EstadoIncidencia,
    EstadoMatricula,
    Estudiante,
    IncidenciaAcademica,
    Matricula,
    Notificacion,
    ObservacionAcademica,
    RecomendacionIA,
)
from sga.roles import (
    ROLE_APODERADO,
    ROLE_DOCENTE,
    ROLE_ESTUDIANTE,
    get_primary_role,
    get_user_profile_ids,
    is_admin_or_directivo,
)


def build_dashboard(user):
    role = get_primary_role(user)
    if is_admin_or_directivo(user):
        return _admin_dashboard(role or "Administrador")
    if role == ROLE_DOCENTE:
        return _docente_dashboard(user)
    if role == ROLE_ESTUDIANTE:
        return _estudiante_dashboard(user)
    if role == ROLE_APODERADO:
        return _apoderado_dashboard(user)
    return {"role": role, "summary": {}, "items": []}


def _admin_dashboard(role):
    return {
        "role": role,
        "summary": {
            "estudiantes": Estudiante.objects.filter(perfil__user__is_active=True).count(),
            "docentes": Docente.objects.filter(perfil__user__is_active=True).count(),
            "apoderados": Apoderado.objects.filter(perfil__user__is_active=True).count(),
            "matriculas_activas": Matricula.objects.filter(estado=EstadoMatricula.ACTIVA).count(),
            "incidencias_abiertas": IncidenciaAcademica.objects.filter(estado=EstadoIncidencia.ABIERTA).count(),
            "notificaciones_pendientes": Notificacion.objects.filter(estado_envio=EstadoEnvio.PENDIENTE, activo=True).count(),
            "recomendaciones_pendientes": RecomendacionIA.objects.filter(estado_revision="PENDIENTE", activo=True).count(),
        },
        "items": [],
    }


def _docente_dashboard(user):
    ids = get_user_profile_ids(user)
    docente_id = ids["docente_id"]
    if docente_id is None:
        return {"role": ROLE_DOCENTE, "summary": {}, "items": []}

    asignaciones = AsignacionCurso.objects.filter(
        docente_id=docente_id,
        estado=EstadoGeneral.ACTIVO,
    )
    seccion_ids = asignaciones.values_list("seccion_id", flat=True)
    anio_ids = asignaciones.values_list("anio_academico_id", flat=True)
    matriculas = Matricula.objects.filter(
        estado=EstadoMatricula.ACTIVA,
        seccion_id__in=seccion_ids,
        anio_academico_id__in=anio_ids,
    )
    matricula_ids = matriculas.values_list("id", flat=True)

    return {
        "role": ROLE_DOCENTE,
        "summary": {
            "cursos_asignados": asignaciones.values("curso_id", "seccion_id", "anio_academico_id").count(),
            "secciones": asignaciones.values("seccion_id").distinct().count(),
            "estudiantes": matriculas.values("estudiante_id").distinct().count(),
            "observaciones_registradas": ObservacionAcademica.objects.filter(docente_id=docente_id, activo=True).count(),
            "incidencias_abiertas": IncidenciaAcademica.objects.filter(matricula_id__in=matricula_ids, estado=EstadoIncidencia.ABIERTA).count(),
            "recomendaciones_pendientes": RecomendacionIA.objects.filter(matricula_id__in=matricula_ids, estado_revision="PENDIENTE", activo=True).count(),
        },
        "items": list(
            asignaciones.select_related("curso", "seccion__grado", "anio_academico")
            .values("id", "curso__nombre", "seccion__nombre", "seccion__grado__nombre", "anio_academico__anio")[:10]
        ),
    }


def _estudiante_dashboard(user):
    ids = get_user_profile_ids(user)
    estudiante_id = ids["estudiante_id"]
    if estudiante_id is None:
        return {"role": ROLE_ESTUDIANTE, "summary": {}, "items": []}

    matriculas = Matricula.objects.filter(estudiante_id=estudiante_id)
    matricula_ids = matriculas.values_list("id", flat=True)
    asignaciones = AsignacionCurso.objects.filter(
        estado=EstadoGeneral.ACTIVO,
        seccion_id__in=matriculas.values_list("seccion_id", flat=True),
        anio_academico_id__in=matriculas.values_list("anio_academico_id", flat=True),
    )

    return {
        "role": ROLE_ESTUDIANTE,
        "summary": {
            "matriculas_activas": matriculas.filter(estado=EstadoMatricula.ACTIVA).count(),
            "cursos": asignaciones.values("curso_id").distinct().count(),
            "asistencias_registradas": Asistencia.objects.filter(matricula_id__in=matricula_ids).count(),
            "calificaciones": Calificacion.objects.filter(matricula_id__in=matricula_ids).count(),
            "incidencias_abiertas": IncidenciaAcademica.objects.filter(matricula_id__in=matricula_ids, estado=EstadoIncidencia.ABIERTA).count(),
            "recomendaciones": RecomendacionIA.objects.filter(matricula_id__in=matricula_ids, activo=True).count(),
        },
        "items": list(
            asignaciones.select_related("curso", "seccion__grado", "anio_academico")
            .values("id", "curso__nombre", "seccion__nombre", "seccion__grado__nombre", "anio_academico__anio")[:10]
        ),
    }


def _apoderado_dashboard(user):
    ids = get_user_profile_ids(user)
    apoderado_id = ids["apoderado_id"]
    if apoderado_id is None:
        return {"role": ROLE_APODERADO, "summary": {}, "items": []}

    estudiante_ids = Estudiante.objects.filter(vinculos_apoderados__apoderado_id=apoderado_id).values_list("id", flat=True)
    matriculas = Matricula.objects.filter(estudiante_id__in=estudiante_ids)
    matricula_ids = matriculas.values_list("id", flat=True)

    return {
        "role": ROLE_APODERADO,
        "summary": {
            "estudiantes": estudiante_ids.count(),
            "matriculas_activas": matriculas.filter(estado=EstadoMatricula.ACTIVA).count(),
            "incidencias_abiertas": IncidenciaAcademica.objects.filter(matricula_id__in=matricula_ids, estado=EstadoIncidencia.ABIERTA).count(),
            "notificaciones_pendientes": Notificacion.objects.filter(apoderado_id=apoderado_id, estado_envio=EstadoEnvio.PENDIENTE, activo=True).count(),
            "notificaciones_enviadas": Notificacion.objects.filter(apoderado_id=apoderado_id, estado_envio=EstadoEnvio.ENVIADA, activo=True).count(),
        },
        "items": list(
            Matricula.objects.filter(estudiante_id__in=estudiante_ids)
            .select_related("estudiante__perfil__user", "seccion__grado", "anio_academico")
            .values(
                "id",
                "estudiante__codigo_estudiante",
                "estudiante__perfil__user__first_name",
                "estudiante__perfil__user__last_name",
                "seccion__nombre",
                "seccion__grado__nombre",
                "anio_academico__anio",
                "estado",
            )[:10]
        ),
    }
