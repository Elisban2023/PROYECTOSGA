from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from sga.models import (
    Asistencia,
    EstadoAsistencia,
    EstadoMatricula,
    Matricula,
    PrioridadNotificacion,
    TipoNotificacion,
)

from .docente import get_asignaciones_docente
from .notificaciones import crear_notificaciones_docente


def get_asistencias_docente(user):
    docente_id = getattr(getattr(getattr(user, "perfil", None), "docente", None), "id", None)
    if docente_id is None:
        return Asistencia.objects.none()
    return Asistencia.objects.filter(
        asignacion_curso__docente_id=docente_id
    ).select_related(
        "matricula__estudiante__perfil__user",
        "asignacion_curso__curso",
        "asignacion_curso__seccion__grado",
    ).prefetch_related("sustentos")


def registrar_asistencias_docente(user, *, asignacion_curso, fecha, registros):
    asignacion = get_asignaciones_docente(user).filter(pk=asignacion_curso).first()
    if asignacion is None:
        raise ValidationError(
            {"asignacion_curso": "No tiene una asignacion activa con ese identificador."}
        )
    if fecha > timezone.localdate():
        raise ValidationError({"fecha": "La fecha de asistencia no puede ser futura."})
    if not asignacion.anio_academico.fecha_inicio <= fecha <= asignacion.anio_academico.fecha_fin:
        raise ValidationError(
            {"fecha": "La fecha debe estar dentro del anio academico de la asignacion."}
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

    creados = 0
    actualizados = 0
    asistencias = []
    with transaction.atomic():
        for registro in registros:
            estado_anterior = (
                Asistencia.objects.filter(
                    matricula=matriculas[registro["matricula"]],
                    asignacion_curso=asignacion,
                    fecha=fecha,
                )
                .values_list("estado", flat=True)
                .first()
            )
            asistencia, creada = Asistencia.objects.update_or_create(
                matricula=matriculas[registro["matricula"]],
                asignacion_curso=asignacion,
                fecha=fecha,
                defaults={
                    "estado": registro["estado"],
                    "justificacion": registro.get("justificacion"),
                },
            )
            creados += int(creada)
            actualizados += int(not creada)
            asistencia._debe_notificar = creada or estado_anterior != asistencia.estado
            asistencias.append(asistencia)
    return asignacion, asistencias, creados, actualizados


def notificar_asistencias_docente(user, asistencias):
    generadas = 0
    for asistencia in asistencias:
        if not getattr(asistencia, "_debe_notificar", True):
            continue
        estudiante = asistencia.matricula.estudiante
        usuarios = [estudiante.perfil.user]
        usuarios.extend(
            vinculo.apoderado.perfil.user
            for vinculo in estudiante.vinculos_apoderados.select_related(
                "apoderado__perfil__user"
            )
            if vinculo.apoderado.perfil.user.is_active
        )
        destinatarios = list(
            dict.fromkeys(usuario.id for usuario in usuarios if usuario.is_active)
        )
        if not destinatarios:
            continue

        estado_label = asistencia.get_estado_display()
        curso = asistencia.asignacion_curso.curso.nombre
        prioridad = (
            PrioridadNotificacion.ALTA
            if asistencia.estado in (EstadoAsistencia.FALTA, EstadoAsistencia.TARDE)
            else PrioridadNotificacion.NORMAL
        )
        creadas = crear_notificaciones_docente(
            user,
            destinatarios=destinatarios,
            titulo=f"Asistencia registrada: {estado_label}",
            mensaje=(
                f"Se registro la asistencia del {asistencia.fecha.strftime('%d/%m/%Y')} "
                f"en el curso {curso} con estado {estado_label}."
            ),
            tipo=TipoNotificacion.ASISTENCIA,
            prioridad=prioridad,
            datos_extra={
                "asistencia_id": asistencia.id,
                "matricula_id": asistencia.matricula_id,
                "asignacion_curso_id": asistencia.asignacion_curso_id,
                "estado": asistencia.estado,
                "puede_justificar": asistencia.estado
                in (EstadoAsistencia.FALTA, EstadoAsistencia.TARDE),
            },
        )
        generadas += len(creadas)
    return generadas
