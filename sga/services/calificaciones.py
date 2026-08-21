from django.db import transaction
from rest_framework.exceptions import ValidationError

from sga.models import (
    Calificacion,
    CriterioCalificacion,
    EstadoAcademico,
    EstadoMatricula,
    EstadoRegistro,
    Matricula,
    PeriodoAcademico,
)

from .docente import get_asignaciones_docente


def get_calificaciones_docente(user):
    docente_id = getattr(getattr(getattr(user, "perfil", None), "docente", None), "id", None)
    if docente_id is None:
        return Calificacion.objects.none()
    return Calificacion.objects.filter(
        asignacion_curso__docente_id=docente_id
    ).select_related(
        "matricula__estudiante__perfil__user",
        "asignacion_curso__curso",
        "asignacion_curso__seccion",
        "periodo_academico",
        "criterio_calificacion__capacidad__competencia",
    )


def registrar_calificaciones_docente(
    user,
    *,
    asignacion_curso,
    periodo_academico,
    criterio_calificacion,
    registros,
):
    asignacion = get_asignaciones_docente(user).filter(pk=asignacion_curso).first()
    if asignacion is None:
        raise ValidationError(
            {"asignacion_curso": "No tiene una asignacion activa con ese identificador."}
        )

    periodo = PeriodoAcademico.objects.filter(pk=periodo_academico).first()
    if periodo is None:
        raise ValidationError({"periodo_academico": "El periodo seleccionado no existe."})
    if periodo.anio_academico_id != asignacion.anio_academico_id:
        raise ValidationError(
            {"periodo_academico": "El periodo no pertenece al anio de la asignacion."}
        )
    if periodo.estado == EstadoAcademico.INACTIVO:
        raise ValidationError({"periodo_academico": "El periodo seleccionado esta inactivo."})

    criterio = CriterioCalificacion.objects.select_related(
        "capacidad__competencia__curso"
    ).filter(pk=criterio_calificacion).first()
    if criterio is None:
        raise ValidationError(
            {"criterio_calificacion": "El criterio seleccionado no existe."}
        )
    capacidad = criterio.capacidad
    competencia = capacidad.competencia
    if (
        criterio.estado != EstadoRegistro.ACTIVO
        or capacidad.estado != EstadoRegistro.ACTIVO
        or competencia.estado != EstadoRegistro.ACTIVO
        or competencia.curso.estado != EstadoRegistro.ACTIVO
    ):
        raise ValidationError(
            {"criterio_calificacion": "El criterio seleccionado esta inactivo."}
        )
    if competencia.curso_id != asignacion.curso_id:
        raise ValidationError(
            {
                "criterio_calificacion": (
                    "El criterio debe pertenecer al curso de la asignacion."
                )
            }
        )

    matricula_ids = {registro["matricula"] for registro in registros}
    matriculas = {
        matricula.id: matricula
        for matricula in Matricula.objects.filter(
            id__in=matricula_ids,
            seccion_id=asignacion.seccion_id,
            anio_academico_id=asignacion.anio_academico_id,
            estado=EstadoMatricula.ACTIVA,
        )
    }
    invalidas = sorted(matricula_ids - matriculas.keys())
    if invalidas:
        raise ValidationError(
            {
                "registros": (
                    "Todas las matriculas deben estar activas y pertenecer a la "
                    "seccion y anio academico de la asignacion. "
                    f"Identificadores invalidos: {invalidas}."
                )
            }
        )

    creadas = 0
    actualizadas = 0
    calificaciones = []
    with transaction.atomic():
        for registro in registros:
            calificacion, creada = Calificacion.objects.update_or_create(
                matricula=matriculas[registro["matricula"]],
                asignacion_curso=asignacion,
                periodo_academico=periodo,
                criterio_calificacion=criterio,
                defaults={
                    "valor": registro["valor"],
                    "observacion": registro.get("observacion"),
                },
            )
            creadas += int(creada)
            actualizadas += int(not creada)
            calificaciones.append(calificacion)
    return asignacion, periodo, criterio, calificaciones, creadas, actualizadas
