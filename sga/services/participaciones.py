from django.utils import timezone
from rest_framework.exceptions import ValidationError

from sga.models import (
    EstadoAcademico,
    EstadoMatricula,
    Matricula,
    Participacion,
    PeriodoAcademico,
)

from .docente import get_asignaciones_docente


def get_participaciones_docente(user):
    docente_id = getattr(getattr(getattr(user, "perfil", None), "docente", None), "id", None)
    if docente_id is None:
        return Participacion.objects.none()
    return Participacion.objects.filter(
        asignacion_curso__docente_id=docente_id
    ).select_related(
        "matricula__estudiante__perfil__user",
        "asignacion_curso__curso",
        "asignacion_curso__seccion__grado",
        "periodo_academico",
    )


def _validar_contexto_participacion(
    user,
    *,
    asignacion_curso,
    matricula,
    fecha,
    periodo_academico,
):
    asignacion = get_asignaciones_docente(user).filter(pk=asignacion_curso).first()
    if asignacion is None:
        raise ValidationError(
            {"asignacion_curso": "No tiene una asignacion activa con ese identificador."}
        )

    fecha_local = timezone.localtime(fecha).date()
    if fecha_local > timezone.localdate():
        raise ValidationError({"fecha": "La fecha de participacion no puede ser futura."})
    if not asignacion.anio_academico.fecha_inicio <= fecha_local <= asignacion.anio_academico.fecha_fin:
        raise ValidationError(
            {"fecha": "La fecha debe estar dentro del anio academico de la asignacion."}
        )

    matricula_obj = Matricula.objects.filter(
        pk=matricula,
        seccion_id=asignacion.seccion_id,
        anio_academico_id=asignacion.anio_academico_id,
        estado=EstadoMatricula.ACTIVA,
    ).first()
    if matricula_obj is None:
        raise ValidationError(
            {
                "matricula": (
                    "La matricula debe estar activa y pertenecer a la seccion y anio "
                    "academico de la asignacion."
                )
            }
        )

    periodo = None
    if periodo_academico is not None:
        periodo = PeriodoAcademico.objects.filter(pk=periodo_academico).first()
        if periodo is None:
            raise ValidationError({"periodo_academico": "El periodo seleccionado no existe."})
        if periodo.anio_academico_id != asignacion.anio_academico_id:
            raise ValidationError(
                {"periodo_academico": "El periodo no pertenece al anio de la asignacion."}
            )
        if periodo.estado == EstadoAcademico.INACTIVO:
            raise ValidationError({"periodo_academico": "El periodo seleccionado esta inactivo."})
        if not periodo.fecha_inicio <= fecha_local <= periodo.fecha_fin:
            raise ValidationError(
                {"fecha": "La fecha debe estar dentro del periodo academico seleccionado."}
            )
    return asignacion, matricula_obj, periodo


def registrar_participacion_docente(user, **datos):
    asignacion, matricula, periodo = _validar_contexto_participacion(
        user,
        asignacion_curso=datos["asignacion_curso"],
        matricula=datos["matricula"],
        fecha=datos["fecha"],
        periodo_academico=datos.get("periodo_academico"),
    )
    return Participacion.objects.create(
        matricula=matricula,
        asignacion_curso=asignacion,
        periodo_academico=periodo,
        fecha=datos["fecha"],
        tipo=datos["tipo"],
        valor=datos.get("valor"),
        observacion=datos.get("observacion"),
    )


def actualizar_participacion_docente(user, participacion, **datos):
    fecha = datos.get("fecha", participacion.fecha)
    periodo_id = datos.get("periodo_academico", participacion.periodo_academico_id)
    _, _, periodo = _validar_contexto_participacion(
        user,
        asignacion_curso=participacion.asignacion_curso_id,
        matricula=participacion.matricula_id,
        fecha=fecha,
        periodo_academico=periodo_id,
    )
    for campo in ("fecha", "tipo", "valor", "observacion"):
        if campo in datos:
            setattr(participacion, campo, datos[campo])
    if "periodo_academico" in datos:
        participacion.periodo_academico = periodo
    participacion.save()
    return participacion
