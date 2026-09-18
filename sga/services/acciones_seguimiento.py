from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from sga.models import (
    AccionSeguimiento,
    ActualizacionAccionSeguimiento,
    EstadoAcademico,
    EstadoAccionSeguimiento,
    EstadoMatricula,
    EstadoIncidencia,
    EstadoRevisionIA,
    IncidenciaAcademica,
    Matricula,
    PeriodoAcademico,
    RecomendacionIA,
    ResponsableAccionSeguimiento,
    TipoActualizacionSeguimiento,
    VinculoApoderado,
)
from sga.services.apoderado import get_vinculos_apoderado
from sga.services.docente import get_asignaciones_docente
from sga.services.estudiante import get_matriculas_estudiante
from sga.services.notificaciones import crear_notificaciones_docente


ESTADOS_CERRADOS = (
    EstadoAccionSeguimiento.COMPLETADA,
    EstadoAccionSeguimiento.CANCELADA,
)


def acciones_base():
    return (
        AccionSeguimiento.objects.filter(activo=True)
        .select_related(
            "matricula__estudiante__perfil__user",
            "asignacion_curso__curso",
            "asignacion_curso__seccion__grado",
            "periodo_academico",
            "docente__perfil__user",
            "incidencia",
            "recomendacion",
        )
        .prefetch_related("actualizaciones__autor")
    )


def get_acciones_docente(user):
    return acciones_base().filter(docente=user.perfil.docente)


def get_acciones_estudiante(user):
    return acciones_base().filter(
        matricula__in=get_matriculas_estudiante(user),
        visible_estudiante=True,
    )


def get_acciones_apoderado(user, *, estudiante_id=None):
    vinculos = get_vinculos_apoderado(user)
    if estudiante_id is not None:
        vinculos = vinculos.filter(estudiante_id=estudiante_id)
        if not vinculos.exists():
            raise ValidationError({"estudiante": "El estudiante no esta vinculado al apoderado."})
    return acciones_base().filter(
        matricula__estudiante_id__in=vinculos.values("estudiante_id"),
        visible_apoderado=True,
    )


def filtrar_acciones(queryset, filtros):
    campos = {
        "asignacion_curso": "asignacion_curso_id",
        "matricula": "matricula_id",
        "docente": "docente_id",
        "periodo_academico": "periodo_academico_id",
        "estado": "estado",
        "prioridad": "prioridad",
        "responsable": "responsable",
    }
    for parametro, campo in campos.items():
        valor = filtros.get(parametro)
        if valor not in (None, ""):
            queryset = queryset.filter(**{campo: valor})
    if str(filtros.get("vencidas", "")).lower() in ("1", "true", "si"):
        queryset = queryset.filter(fecha_limite__lt=timezone.localdate()).exclude(
            estado__in=ESTADOS_CERRADOS
        )
    return queryset


def crear_accion_docente(user, datos):
    asignacion = get_asignaciones_docente(user).filter(
        pk=datos["asignacion_curso_id"]
    ).first()
    if asignacion is None:
        raise ValidationError(
            {"asignacion_curso_id": "No tiene una asignacion activa con ese identificador."}
        )
    matricula = Matricula.objects.filter(
        pk=datos["matricula_id"],
        seccion_id=asignacion.seccion_id,
        anio_academico_id=asignacion.anio_academico_id,
        estado=EstadoMatricula.ACTIVA,
    ).select_related("estudiante__perfil__user").first()
    if matricula is None:
        raise ValidationError(
            {"matricula_id": "La matricula no pertenece a la seccion y anio del curso."}
        )

    periodo = _periodo_valido(matricula, datos.get("periodo_academico_id"))
    incidencia = _incidencia_valida(
        asignacion,
        matricula,
        datos.get("incidencia_id"),
    )
    recomendacion = _recomendacion_valida(
        asignacion,
        matricula,
        datos.get("recomendacion_id"),
    )
    notificar = datos.get("notificar_destinatarios", True)
    campos = {
        clave: valor
        for clave, valor in datos.items()
        if clave
        not in {
            "matricula_id",
            "asignacion_curso_id",
            "periodo_academico_id",
            "incidencia_id",
            "recomendacion_id",
            "notificar_destinatarios",
        }
    }
    with transaction.atomic():
        accion = AccionSeguimiento.objects.create(
            matricula=matricula,
            asignacion_curso=asignacion,
            periodo_academico=periodo,
            docente=user.perfil.docente,
            incidencia=incidencia,
            recomendacion=recomendacion,
            **campos,
        )

    notificaciones = _notificar_nueva_accion(user, accion) if notificar else []
    return accion, notificaciones


def actualizar_accion_docente(user, accion_id, datos):
    accion = get_acciones_docente(user).filter(pk=accion_id).first()
    if accion is None:
        raise NotFound("La accion no existe o no pertenece al docente autenticado.")
    if accion.estado in ESTADOS_CERRADOS:
        raise ValidationError({"accion": "Una accion cerrada ya no puede modificarse."})
    estado = datos.get("estado", accion.estado)
    resultado = (datos.get("resultado", accion.resultado) or "").strip()
    if estado in ESTADOS_CERRADOS and len(resultado) < 10:
        raise ValidationError(
            {"resultado": "Registre el resultado o motivo para cerrar la accion."}
        )
    for campo, valor in datos.items():
        setattr(accion, campo, valor)
    if estado == EstadoAccionSeguimiento.COMPLETADA:
        accion.fecha_completada = accion.fecha_completada or timezone.now()
    elif estado not in ESTADOS_CERRADOS:
        accion.fecha_completada = None
    accion.save()
    return accion


def crear_actualizacion(user, accion, datos, *, rol):
    if accion.estado in ESTADOS_CERRADOS:
        raise ValidationError({"accion": "No se pueden agregar avances a una accion cerrada."})
    responsables_avance = {
        "Estudiante": (
            ResponsableAccionSeguimiento.ESTUDIANTE,
            ResponsableAccionSeguimiento.COMPARTIDA,
        ),
        "Apoderado": (
            ResponsableAccionSeguimiento.APODERADO,
            ResponsableAccionSeguimiento.COMPARTIDA,
        ),
    }
    permitidos = responsables_avance.get(rol)
    if (
        datos["tipo"] == TipoActualizacionSeguimiento.AVANCE
        and permitidos is not None
        and accion.responsable not in permitidos
    ):
        raise ValidationError(
            {"tipo": "El usuario puede informar avances solo cuando es responsable de la accion."}
        )
    actualizacion = ActualizacionAccionSeguimiento.objects.create(
        accion=accion,
        autor=user,
        **datos,
    )
    if (
        datos["tipo"] == TipoActualizacionSeguimiento.AVANCE
        and (datos.get("progreso") or 0) > 0
        and accion.estado == EstadoAccionSeguimiento.PENDIENTE
    ):
        accion.estado = EstadoAccionSeguimiento.EN_PROGRESO
        accion.save(update_fields=["estado", "actualizado_en"])
    return actualizacion


def get_accion_para_actualizar(user, accion_id, rol):
    if rol == "Docente":
        queryset = get_acciones_docente(user)
    elif rol == "Estudiante":
        queryset = get_acciones_estudiante(user)
    elif rol == "Apoderado":
        queryset = get_acciones_apoderado(user)
    else:
        raise NotFound("No tiene acceso a la accion de seguimiento.")
    accion = queryset.filter(pk=accion_id).first()
    if accion is None:
        raise NotFound("No tiene acceso a la accion de seguimiento.")
    return accion


def _periodo_valido(matricula, periodo_id):
    if periodo_id is None:
        return None
    periodo = PeriodoAcademico.objects.filter(
        pk=periodo_id,
        anio_academico_id=matricula.anio_academico_id,
    ).first()
    if periodo is None or periodo.estado == EstadoAcademico.INACTIVO:
        raise ValidationError(
            {"periodo_academico_id": "El periodo no pertenece al anio o esta inactivo."}
        )
    return periodo


def _incidencia_valida(asignacion, matricula, incidencia_id):
    if incidencia_id is None:
        return None
    incidencia = IncidenciaAcademica.objects.filter(
        pk=incidencia_id,
        matricula=matricula,
        observacion__asignacion_curso=asignacion,
        observacion__docente=asignacion.docente,
    ).first()
    if incidencia is None:
        raise ValidationError(
            {"incidencia_id": "La incidencia no corresponde al estudiante y curso."}
        )
    if incidencia.estado == EstadoIncidencia.CERRADA:
        raise ValidationError(
            {"incidencia_id": "No se puede crear una accion desde una incidencia cerrada."}
        )
    return incidencia


def _recomendacion_valida(asignacion, matricula, recomendacion_id):
    if recomendacion_id is None:
        return None
    recomendacion = RecomendacionIA.objects.filter(
        pk=recomendacion_id,
        matricula=matricula,
        asignacion_curso=asignacion,
        estado_revision__in=(EstadoRevisionIA.APROBADA, EstadoRevisionIA.EDITADA),
        activo=True,
    ).first()
    if recomendacion is None:
        raise ValidationError(
            {"recomendacion_id": "La recomendacion debe pertenecer al curso y estar revisada."}
        )
    return recomendacion


def _notificar_nueva_accion(user, accion):
    destinatarios = []
    estudiante_user = accion.matricula.estudiante.perfil.user
    if accion.visible_estudiante and estudiante_user.is_active:
        destinatarios.append((estudiante_user, "/estudiante/mi-seguimiento"))
    if accion.visible_apoderado:
        vinculos = VinculoApoderado.objects.filter(
            estudiante=accion.matricula.estudiante,
            apoderado__perfil__user__is_active=True,
        ).select_related("apoderado__perfil__user")
        destinatarios.extend(
            (vinculo.apoderado.perfil.user, "/apoderado/seguimiento")
            for vinculo in vinculos
        )

    notificaciones = []
    for destinatario, ruta in destinatarios:
        notificaciones.extend(
            crear_notificaciones_docente(
                user,
                destinatarios=[destinatario.id],
                tipo="ACADEMICA",
                prioridad=accion.prioridad,
                titulo=f"Nueva accion de seguimiento: {accion.titulo}",
                mensaje=accion.descripcion,
                accion_url=ruta,
                incidencia_id=accion.incidencia_id,
                recomendacion=accion.recomendacion,
                datos_extra={
                    "accion_seguimiento_id": accion.id,
                    "matricula_id": accion.matricula_id,
                    "asignacion_curso_id": accion.asignacion_curso_id,
                },
            )
        )
    return notificaciones
