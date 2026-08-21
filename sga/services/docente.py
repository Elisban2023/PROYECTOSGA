from django.db.models import Count, F, Q

from sga.models import AsignacionCurso, EstadoGeneral, EstadoMatricula
from sga.roles import get_user_profile_ids


def get_asignaciones_docente(user):
    docente_id = get_user_profile_ids(user)["docente_id"]
    if docente_id is None:
        return AsignacionCurso.objects.none()

    return (
        AsignacionCurso.objects.filter(
            docente_id=docente_id,
            estado=EstadoGeneral.ACTIVO,
        )
        .select_related("curso", "seccion__grado", "anio_academico")
        .annotate(
            estudiantes_matriculados=Count(
                "seccion__matriculas",
                filter=Q(
                    seccion__matriculas__anio_academico=F("anio_academico"),
                    seccion__matriculas__estado=EstadoMatricula.ACTIVA,
                ),
                distinct=True,
            )
        )
        .order_by(
            "-anio_academico__anio",
            "seccion__grado__nivel",
            "seccion__grado__nombre",
            "seccion__nombre",
            "curso__nombre",
        )
    )
