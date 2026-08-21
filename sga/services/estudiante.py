from django.db.models import Q

from sga.models import AsignacionCurso, EstadoGeneral, EstadoMatricula


def get_matriculas_estudiante(user):
    estudiante_id = getattr(getattr(getattr(user, "perfil", None), "estudiante", None), "id", None)
    if estudiante_id is None:
        return []
    return list(
        user.perfil.estudiante.matriculas.filter(
            estado=EstadoMatricula.ACTIVA,
        ).select_related("seccion__grado", "anio_academico").order_by("-anio_academico__anio")
    )


def get_asignaciones_estudiante(user):
    matriculas = get_matriculas_estudiante(user)
    if not matriculas:
        return AsignacionCurso.objects.none()
    condition = Q()
    for matricula in matriculas:
        condition |= Q(
            seccion_id=matricula.seccion_id,
            anio_academico_id=matricula.anio_academico_id,
        )
    return AsignacionCurso.objects.filter(
        condition,
        estado=EstadoGeneral.ACTIVO,
    ).select_related(
        "curso", "seccion__grado", "anio_academico", "docente__perfil__user"
    ).order_by("-anio_academico__anio", "curso__nombre")
