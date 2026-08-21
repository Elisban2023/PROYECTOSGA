from django.utils import timezone
from rest_framework.exceptions import ValidationError

from sga.models import EstadoMatricula, Matricula, ObservacionAcademica

from .docente import get_asignaciones_docente


def get_observaciones_docente(user):
    docente_id = getattr(getattr(getattr(user, "perfil", None), "docente", None), "id", None)
    if docente_id is None:
        return ObservacionAcademica.objects.none()
    return ObservacionAcademica.objects.filter(docente_id=docente_id).select_related(
        "matricula__estudiante__perfil__user",
        "asignacion_curso__curso",
        "asignacion_curso__seccion__grado",
    )


def _validar_contexto_observacion(user, *, asignacion_curso, matricula, fecha):
    asignacion = get_asignaciones_docente(user).filter(pk=asignacion_curso).first()
    if asignacion is None:
        raise ValidationError(
            {"asignacion_curso": "No tiene una asignacion activa con ese identificador."}
        )
    fecha_local = timezone.localtime(fecha).date()
    if fecha > timezone.now():
        raise ValidationError({"fecha": "La fecha de observacion no puede ser futura."})
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
    return asignacion, matricula_obj


def registrar_observacion_docente(user, **datos):
    asignacion, matricula = _validar_contexto_observacion(
        user,
        asignacion_curso=datos["asignacion_curso"],
        matricula=datos["matricula"],
        fecha=datos["fecha"],
    )
    return ObservacionAcademica.objects.create(
        matricula=matricula,
        asignacion_curso=asignacion,
        docente=user.perfil.docente,
        fecha=datos["fecha"],
        categoria=datos["categoria"],
        descripcion=datos["descripcion"],
    )


def actualizar_observacion_docente(user, observacion, **datos):
    fecha = datos.get("fecha", observacion.fecha)
    _validar_contexto_observacion(
        user,
        asignacion_curso=observacion.asignacion_curso_id,
        matricula=observacion.matricula_id,
        fecha=fecha,
    )
    for campo in ("fecha", "categoria", "descripcion"):
        if campo in datos:
            setattr(observacion, campo, datos[campo])
    observacion.save(update_fields=[*datos.keys()])
    return observacion
