from collections import defaultdict

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from sga.models import (
    AccionSeguimiento,
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Asistencia,
    Calificacion,
    Docente,
    EstadoAsistencia,
    EstadoAccionSeguimiento,
    EstadoEnvio,
    EstadoGeneral,
    EstadoIncidencia,
    EstadoMatricula,
    EstadoRevisionIA,
    Estudiante,
    Grado,
    IncidenciaAcademica,
    Matricula,
    NivelIncidencia,
    NivelLogro,
    Notificacion,
    ObservacionAcademica,
    Participacion,
    PeriodoAcademico,
    RecomendacionIA,
    Seccion,
)
from sga.roles import (
    ROLE_APODERADO,
    ROLE_DOCENTE,
    ROLE_ESTUDIANTE,
    get_primary_role,
    get_user_profile_ids,
    is_admin_or_directivo,
)


UMBRAL_ASISTENCIA_ALERTA = 80


def build_dashboard(user, filtros=None):
    filtros = _normalizar_filtros(filtros or {})
    role = get_primary_role(user)
    if is_admin_or_directivo(user):
        return _admin_dashboard(role or "Administrador", filtros)
    if role == ROLE_DOCENTE:
        return _docente_dashboard(user, filtros)
    if role == ROLE_ESTUDIANTE:
        return _estudiante_dashboard(user, filtros)
    if role == ROLE_APODERADO:
        return _apoderado_dashboard(user, filtros)
    return _respuesta_vacia(role, filtros)


def _admin_dashboard(role, filtros):
    asignaciones = _filtrar_asignaciones(AsignacionCurso.objects.all(), filtros)
    matriculas = _matriculas_de_asignaciones(asignaciones)
    matriculas = _filtrar_matriculas(matriculas, filtros)
    periodo = _resolver_periodo(filtros, matriculas)
    registros = _registros_academicos(matriculas, asignaciones, periodo, filtros)
    metricas = _metricas_academicas(registros)
    prioridades = _prioridades_estudiantes(matriculas, registros)

    docentes_ids = asignaciones.values_list("docente_id", flat=True).distinct()
    incidencias_sin_resolver = registros["incidencias"].exclude(estado=EstadoIncidencia.CERRADA).count()
    resumen = {
        "estudiantes": Estudiante.objects.filter(perfil__user__is_active=True).count(),
        "docentes": Docente.objects.filter(perfil__user__is_active=True).count(),
        "apoderados": Apoderado.objects.filter(perfil__user__is_active=True).count(),
        "matriculas_activas": matriculas.filter(estado=EstadoMatricula.ACTIVA).count(),
        "incidencias_abiertas": registros["incidencias"].filter(estado=EstadoIncidencia.ABIERTA).count(),
        "notificaciones_pendientes": Notificacion.objects.filter(
            estado_envio=EstadoEnvio.PENDIENTE, activo=True
        ).count(),
        "recomendaciones_pendientes": registros["recomendaciones"].filter(
            estado_revision=EstadoRevisionIA.PENDIENTE
        ).count(),
        "docentes_en_contexto": docentes_ids.count(),
        "estudiantes_priorizados": len(prioridades),
        **_resumen_acciones(registros["acciones"]),
    }
    return _armar_respuesta(
        role,
        filtros,
        resumen,
        _indicadores(metricas, incidencias_sin_resolver, len(prioridades)),
        _graficos(registros, metricas, incluir_docentes=True),
        prioridades,
        _opciones_admin(),
    )


def _docente_dashboard(user, filtros):
    _rechazar_filtros(filtros, {"docente", "estudiante"})
    docente_id = get_user_profile_ids(user)["docente_id"]
    if docente_id is None:
        return _respuesta_vacia(ROLE_DOCENTE, filtros)

    asignaciones = _filtrar_asignaciones(
        AsignacionCurso.objects.filter(docente_id=docente_id), filtros
    )
    matriculas = _filtrar_matriculas(_matriculas_de_asignaciones(asignaciones), filtros)
    periodo = _resolver_periodo(filtros, matriculas)
    registros = _registros_academicos(matriculas, asignaciones, periodo, filtros)
    registros["observaciones"] = registros["observaciones"].filter(docente_id=docente_id)
    registros["incidencias"] = registros["incidencias"].filter(
        Q(observacion__docente_id=docente_id) | Q(observacion__isnull=True)
    )
    registros["acciones"] = registros["acciones"].filter(docente_id=docente_id)
    metricas = _metricas_academicas(registros)
    prioridades = _prioridades_estudiantes(matriculas, registros)
    incidencias_sin_resolver = registros["incidencias"].exclude(estado=EstadoIncidencia.CERRADA).count()

    resumen = {
        "cursos_asignados": asignaciones.values("curso_id", "seccion_id", "anio_academico_id").count(),
        "secciones": asignaciones.values("seccion_id").distinct().count(),
        "estudiantes": matriculas.values("estudiante_id").distinct().count(),
        "observaciones_registradas": registros["observaciones"].count(),
        "incidencias_abiertas": registros["incidencias"].filter(estado=EstadoIncidencia.ABIERTA).count(),
        "recomendaciones_pendientes": registros["recomendaciones"].filter(
            estado_revision=EstadoRevisionIA.PENDIENTE
        ).count(),
        "estudiantes_priorizados": len(prioridades),
        **_resumen_acciones(registros["acciones"]),
    }
    return _armar_respuesta(
        ROLE_DOCENTE,
        filtros,
        resumen,
        _indicadores(metricas, incidencias_sin_resolver, len(prioridades)),
        _graficos(registros, metricas),
        prioridades,
        _opciones_asignaciones(asignaciones),
        items=_serializar_asignaciones(asignaciones),
    )


def _estudiante_dashboard(user, filtros):
    _rechazar_filtros(filtros, {"docente", "estudiante", "grado", "seccion"})
    estudiante_id = get_user_profile_ids(user)["estudiante_id"]
    if estudiante_id is None:
        return _respuesta_vacia(ROLE_ESTUDIANTE, filtros)

    matriculas = _filtrar_matriculas(
        Matricula.objects.filter(estudiante_id=estudiante_id), filtros
    )
    asignaciones = _filtrar_asignaciones(_asignaciones_de_matriculas(matriculas), filtros)
    periodo = _resolver_periodo(filtros, matriculas)
    registros = _registros_academicos(matriculas, asignaciones, periodo, filtros)
    registros["recomendaciones"] = registros["recomendaciones"].filter(
        estado_revision__in=(EstadoRevisionIA.APROBADA, EstadoRevisionIA.EDITADA)
    )
    registros["acciones"] = registros["acciones"].filter(visible_estudiante=True)
    metricas = _metricas_academicas(registros)
    incidencias_sin_resolver = registros["incidencias"].exclude(estado=EstadoIncidencia.CERRADA).count()
    prioridades = _prioridades_estudiantes(matriculas, registros)

    resumen = {
        "matriculas_activas": matriculas.filter(estado=EstadoMatricula.ACTIVA).count(),
        "cursos": asignaciones.values("curso_id").distinct().count(),
        "asistencias_registradas": registros["asistencias"].count(),
        "calificaciones": registros["calificaciones"].count(),
        "incidencias_abiertas": registros["incidencias"].filter(estado=EstadoIncidencia.ABIERTA).count(),
        "recomendaciones": registros["recomendaciones"].count(),
        **_resumen_acciones(registros["acciones"]),
    }
    return _armar_respuesta(
        ROLE_ESTUDIANTE,
        filtros,
        resumen,
        _indicadores(metricas, incidencias_sin_resolver, len(prioridades)),
        _graficos(registros, metricas, incluir_participacion=True),
        prioridades,
        _opciones_asignaciones(asignaciones),
        items=_serializar_asignaciones(asignaciones),
    )


def _apoderado_dashboard(user, filtros):
    _rechazar_filtros(filtros, {"docente", "grado", "seccion", "asignacion_curso"})
    apoderado_id = get_user_profile_ids(user)["apoderado_id"]
    if apoderado_id is None:
        return _respuesta_vacia(ROLE_APODERADO, filtros)

    estudiantes = Estudiante.objects.filter(vinculos_apoderados__apoderado_id=apoderado_id)
    if filtros.get("estudiante"):
        estudiantes = estudiantes.filter(id=filtros["estudiante"])
        if not estudiantes.exists():
            raise ValidationError({"estudiante": "El estudiante no esta vinculado con este apoderado."})

    matriculas = _filtrar_matriculas(
        Matricula.objects.filter(estudiante_id__in=estudiantes.values("id")), filtros
    )
    asignaciones = _asignaciones_de_matriculas(matriculas)
    periodo = _resolver_periodo(filtros, matriculas)
    registros = _registros_academicos(matriculas, asignaciones, periodo, filtros)
    registros["recomendaciones"] = registros["recomendaciones"].filter(
        estado_revision__in=(EstadoRevisionIA.APROBADA, EstadoRevisionIA.EDITADA)
    )
    registros["acciones"] = registros["acciones"].filter(visible_apoderado=True)
    metricas = _metricas_academicas(registros)
    prioridades = _prioridades_estudiantes(matriculas, registros)
    incidencias_sin_resolver = registros["incidencias"].exclude(estado=EstadoIncidencia.CERRADA).count()
    resumen = {
        "estudiantes": estudiantes.distinct().count(),
        "matriculas_activas": matriculas.filter(estado=EstadoMatricula.ACTIVA).count(),
        "incidencias_abiertas": registros["incidencias"].filter(estado=EstadoIncidencia.ABIERTA).count(),
        "notificaciones_pendientes": Notificacion.objects.filter(
            apoderado_id=apoderado_id, estado_envio=EstadoEnvio.PENDIENTE, activo=True
        ).count(),
        "notificaciones_enviadas": Notificacion.objects.filter(
            apoderado_id=apoderado_id, estado_envio=EstadoEnvio.ENVIADA, activo=True
        ).count(),
        "estudiantes_priorizados": len(prioridades),
        **_resumen_acciones(registros["acciones"]),
    }
    return _armar_respuesta(
        ROLE_APODERADO,
        filtros,
        resumen,
        _indicadores(metricas, incidencias_sin_resolver, len(prioridades)),
        _graficos(registros, metricas),
        prioridades,
        _opciones_apoderado(estudiantes),
        items=_serializar_matriculas(matriculas),
    )


def _registros_academicos(matriculas, asignaciones, periodo, filtros):
    matricula_ids = matriculas.values_list("id", flat=True)
    asignacion_ids = asignaciones.values_list("id", flat=True)
    asistencias = Asistencia.objects.filter(
        matricula_id__in=matricula_ids, asignacion_curso_id__in=asignacion_ids
    )
    calificaciones = Calificacion.objects.filter(
        matricula_id__in=matricula_ids, asignacion_curso_id__in=asignacion_ids
    )
    participaciones = Participacion.objects.filter(
        matricula_id__in=matricula_ids, asignacion_curso_id__in=asignacion_ids
    )
    observaciones = ObservacionAcademica.objects.filter(
        matricula_id__in=matricula_ids, activo=True
    ).filter(Q(asignacion_curso_id__in=asignacion_ids) | Q(asignacion_curso__isnull=True))
    incidencias = IncidenciaAcademica.objects.filter(matricula_id__in=matricula_ids)
    recomendaciones = RecomendacionIA.objects.filter(
        matricula_id__in=matricula_ids, activo=True
    ).filter(Q(asignacion_curso_id__in=asignacion_ids) | Q(asignacion_curso__isnull=True))
    acciones = AccionSeguimiento.objects.filter(
        matricula_id__in=matricula_ids,
        asignacion_curso_id__in=asignacion_ids,
        activo=True,
    )

    if periodo:
        asistencias = asistencias.filter(fecha__range=(periodo.fecha_inicio, periodo.fecha_fin))
        calificaciones = calificaciones.filter(periodo_academico=periodo)
        participaciones = participaciones.filter(periodo_academico=periodo)
        observaciones = observaciones.filter(fecha__date__range=(periodo.fecha_inicio, periodo.fecha_fin))
        incidencias = incidencias.filter(fecha_registro__date__range=(periodo.fecha_inicio, periodo.fecha_fin))
        recomendaciones = recomendaciones.filter(periodo_academico=periodo)
        acciones = acciones.filter(Q(periodo_academico=periodo) | Q(periodo_academico__isnull=True))
    elif filtros.get("anio_academico"):
        anio = AnioAcademico.objects.filter(id=filtros["anio_academico"]).first()
        if anio:
            asistencias = asistencias.filter(fecha__range=(anio.fecha_inicio, anio.fecha_fin))
            observaciones = observaciones.filter(fecha__date__range=(anio.fecha_inicio, anio.fecha_fin))
            incidencias = incidencias.filter(fecha_registro__date__range=(anio.fecha_inicio, anio.fecha_fin))
            acciones = acciones.filter(
                Q(periodo_academico__anio_academico=anio)
                | Q(periodo_academico__isnull=True, asignacion_curso__anio_academico=anio)
            )

    return {
        "asistencias": asistencias,
        "calificaciones": calificaciones,
        "participaciones": participaciones,
        "observaciones": observaciones,
        "incidencias": incidencias,
        "recomendaciones": recomendaciones,
        "acciones": acciones,
    }


def _metricas_academicas(registros):
    asistencia = _conteos_choices(registros["asistencias"], "estado", EstadoAsistencia.values)
    notas = _conteos_choices(registros["calificaciones"], "valor", NivelLogro.values)
    total_asistencia = sum(asistencia.values())
    asistencias_validas = asistencia[EstadoAsistencia.PRESENTE] + asistencia[EstadoAsistencia.JUSTIFICADA]
    total_notas = sum(notas.values())
    bajo_logro = notas[NivelLogro.B] + notas[NivelLogro.C]
    return {
        "asistencia": asistencia,
        "calificaciones": notas,
        "porcentaje_asistencia": _porcentaje(asistencias_validas, total_asistencia),
        "porcentaje_b_c": _porcentaje(bajo_logro, total_notas),
        "total_asistencias": total_asistencia,
        "total_calificaciones": total_notas,
    }


def _indicadores(metricas, incidencias_sin_resolver, estudiantes_priorizados):
    return [
        _indicador(
            "asistencia",
            "Asistencia efectiva",
            metricas["porcentaje_asistencia"],
            "%",
            "Porcentaje de presentes y faltas justificadas sobre registros de asistencia.",
            _estado_asistencia(metricas),
        ),
        _indicador(
            "evidencias_b_c",
            "Evidencias en B o C",
            metricas["porcentaje_b_c"],
            "%",
            "Proporcion de calificaciones en proceso o en inicio.",
            "alerta" if metricas["porcentaje_b_c"] > 0 else "bien",
        ),
        _indicador(
            "incidencias_sin_resolver",
            "Incidencias sin resolver",
            incidencias_sin_resolver,
            "registros",
            "Incidencias abiertas o en seguimiento dentro del filtro aplicado.",
            "alerta" if incidencias_sin_resolver else "bien",
        ),
        _indicador(
            "estudiantes_priorizados",
            "Seguimiento prioritario",
            estudiantes_priorizados,
            "estudiantes",
            "Casos con asistencia menor al 80%, evidencias B/C o incidencias pendientes.",
            "alerta" if estudiantes_priorizados else "bien",
        ),
    ]


def _graficos(registros, metricas, incluir_docentes=False, incluir_participacion=False):
    graficos = [
        {
            "id": "distribucion_asistencia",
            "titulo": "Distribucion de asistencia",
            "tipo": "donut",
            "datos": _datos_choices(metricas["asistencia"], EstadoAsistencia.choices),
        },
        {
            "id": "niveles_logro",
            "titulo": "Niveles de logro AD, A, B y C",
            "tipo": "barras",
            "datos": _datos_choices(metricas["calificaciones"], NivelLogro.choices),
        },
        {
            "id": "estado_incidencias",
            "titulo": "Estado de incidencias",
            "tipo": "barras",
            "datos": _distribucion(registros["incidencias"], "estado", EstadoIncidencia.choices),
        },
        {
            "id": "nivel_incidencias",
            "titulo": "Nivel de incidencias",
            "tipo": "barras",
            "datos": _distribucion(registros["incidencias"], "nivel", NivelIncidencia.choices),
        },
        {
            "id": "estado_acciones_seguimiento",
            "titulo": "Estado de acciones de seguimiento",
            "tipo": "barras",
            "datos": _distribucion(
                registros["acciones"],
                "estado",
                EstadoAccionSeguimiento.choices,
            ),
        },
    ]
    if incluir_participacion:
        graficos.append(
            {
                "id": "participaciones_por_curso",
                "titulo": "Participaciones registradas por curso",
                "tipo": "barras",
                "datos": _agrupar(registros["participaciones"], "asignacion_curso__curso__nombre"),
            }
        )
    if incluir_docentes:
        graficos.append(
            {
                "id": "seguimiento_por_docente",
                "titulo": "Seguimiento registrado por docente",
                "tipo": "barras_apiladas",
                "datos": _seguimiento_por_docente(registros),
            }
        )
    return graficos


def _prioridades_estudiantes(matriculas, registros):
    datos = defaultdict(lambda: {"asistencia_total": 0, "asistencia_valida": 0, "b": 0, "c": 0, "incidencias": 0})
    for fila in registros["asistencias"].values("matricula_id", "estado"):
        item = datos[fila["matricula_id"]]
        item["asistencia_total"] += 1
        if fila["estado"] in (EstadoAsistencia.PRESENTE, EstadoAsistencia.JUSTIFICADA):
            item["asistencia_valida"] += 1
    for fila in registros["calificaciones"].values("matricula_id", "valor"):
        if fila["valor"] == NivelLogro.B:
            datos[fila["matricula_id"]]["b"] += 1
        elif fila["valor"] == NivelLogro.C:
            datos[fila["matricula_id"]]["c"] += 1
    for fila in registros["incidencias"].exclude(estado=EstadoIncidencia.CERRADA).values("matricula_id"):
        datos[fila["matricula_id"]]["incidencias"] += 1

    resultado = []
    filas = matriculas.select_related(
        "estudiante__perfil__user", "seccion__grado", "anio_academico"
    )
    for matricula in filas:
        item = datos[matricula.id]
        porcentaje = _porcentaje(item["asistencia_valida"], item["asistencia_total"])
        motivos = []
        if item["asistencia_total"] and porcentaje < UMBRAL_ASISTENCIA_ALERTA:
            motivos.append("asistencia menor al 80%")
        if item["c"]:
            motivos.append(f"{item['c']} evidencia(s) en C")
        if item["b"]:
            motivos.append(f"{item['b']} evidencia(s) en B")
        if item["incidencias"]:
            motivos.append(f"{item['incidencias']} incidencia(s) sin resolver")
        if not motivos:
            continue
        user = matricula.estudiante.perfil.user
        resultado.append(
            {
                "matricula_id": matricula.id,
                "estudiante_id": matricula.estudiante_id,
                "codigo_estudiante": matricula.estudiante.codigo_estudiante,
                "estudiante": user.get_full_name().strip() or user.username,
                "grado": matricula.seccion.grado.nombre,
                "seccion": matricula.seccion.nombre,
                "porcentaje_asistencia": porcentaje if item["asistencia_total"] else None,
                "evidencias_b": item["b"],
                "evidencias_c": item["c"],
                "incidencias_sin_resolver": item["incidencias"],
                "motivos": motivos,
                "nivel_atencion": "alta" if item["c"] or item["incidencias"] else "media",
            }
        )
    return sorted(
        resultado,
        key=lambda item: (item["nivel_atencion"] != "alta", -(item["evidencias_c"] + item["incidencias_sin_resolver"])),
    )[:20]


def _resumen_acciones(queryset):
    abiertas = queryset.filter(
        estado__in=(
            EstadoAccionSeguimiento.PENDIENTE,
            EstadoAccionSeguimiento.EN_PROGRESO,
        )
    )
    return {
        "acciones_seguimiento_pendientes": abiertas.count(),
        "acciones_seguimiento_vencidas": abiertas.filter(
            fecha_limite__lt=timezone.localdate()
        ).count(),
        "acciones_seguimiento_completadas": queryset.filter(
            estado=EstadoAccionSeguimiento.COMPLETADA
        ).count(),
    }


def _armar_respuesta(role, filtros, resumen, indicadores, graficos, prioridades, opciones, items=None):
    return {
        "role": role,
        "filtros_aplicados": filtros,
        "opciones_filtro": opciones,
        "summary": resumen,
        "indicadores": indicadores,
        "graficos": graficos,
        "prioridades": prioridades,
        "items": items if items is not None else prioridades,
        "meta": {
            "generado_en": timezone.now(),
            "criterio_priorizacion": (
                "Orientativo: asistencia efectiva menor al 80%, calificaciones B/C o incidencias sin resolver. "
                "Requiere interpretacion humana y no constituye diagnostico."
            ),
            "sin_datos_es_cero": True,
        },
    }


def _respuesta_vacia(role, filtros):
    return _armar_respuesta(role, filtros, {}, [], [], [], {})


def _filtrar_asignaciones(queryset, filtros):
    campos = {
        "anio_academico": "anio_academico_id",
        "grado": "seccion__grado_id",
        "seccion": "seccion_id",
        "docente": "docente_id",
        "asignacion_curso": "id",
    }
    for parametro, campo in campos.items():
        if filtros.get(parametro):
            queryset = queryset.filter(**{campo: filtros[parametro]})
    return queryset.filter(estado=EstadoGeneral.ACTIVO)


def _filtrar_matriculas(queryset, filtros):
    campos = {
        "anio_academico": "anio_academico_id",
        "grado": "seccion__grado_id",
        "seccion": "seccion_id",
        "estudiante": "estudiante_id",
    }
    for parametro, campo in campos.items():
        if filtros.get(parametro):
            queryset = queryset.filter(**{campo: filtros[parametro]})
    return queryset


def _matriculas_de_asignaciones(asignaciones):
    pares = asignaciones.values_list("seccion_id", "anio_academico_id").distinct()
    condicion = Q(pk__in=[])
    for seccion_id, anio_id in pares:
        condicion |= Q(seccion_id=seccion_id, anio_academico_id=anio_id)
    return Matricula.objects.filter(condicion)


def _asignaciones_de_matriculas(matriculas):
    pares = matriculas.values_list("seccion_id", "anio_academico_id").distinct()
    condicion = Q(pk__in=[])
    for seccion_id, anio_id in pares:
        condicion |= Q(seccion_id=seccion_id, anio_academico_id=anio_id)
    return AsignacionCurso.objects.filter(condicion, estado=EstadoGeneral.ACTIVO)


def _resolver_periodo(filtros, matriculas):
    periodo_id = filtros.get("periodo_academico")
    if not periodo_id:
        return None
    periodo = PeriodoAcademico.objects.filter(id=periodo_id).first()
    if periodo is None:
        raise ValidationError({"periodo_academico": "El periodo academico no existe."})
    if filtros.get("anio_academico") and periodo.anio_academico_id != filtros["anio_academico"]:
        raise ValidationError({"periodo_academico": "El periodo no pertenece al anio seleccionado."})
    if not matriculas.filter(anio_academico_id=periodo.anio_academico_id).exists():
        raise ValidationError({"periodo_academico": "El periodo no corresponde al alcance del usuario."})
    return periodo


def _normalizar_filtros(filtros):
    filtros = dict(filtros)
    periodo_id = filtros.get("periodo_academico")
    if not periodo_id:
        return filtros
    periodo = PeriodoAcademico.objects.filter(id=periodo_id).first()
    if periodo is None:
        raise ValidationError({"periodo_academico": "El periodo academico no existe."})
    if filtros.get("anio_academico") and filtros["anio_academico"] != periodo.anio_academico_id:
        raise ValidationError({"periodo_academico": "El periodo no pertenece al anio seleccionado."})
    filtros.setdefault("anio_academico", periodo.anio_academico_id)
    return filtros


def _rechazar_filtros(filtros, no_permitidos):
    errores = {
        campo: "Este filtro no esta disponible para el rol autenticado."
        for campo in no_permitidos
        if filtros.get(campo)
    }
    if errores:
        raise ValidationError(errores)


def _opciones_admin():
    asignaciones = AsignacionCurso.objects.filter(estado=EstadoGeneral.ACTIVO)
    return {
        "anios_academicos": list(AnioAcademico.objects.order_by("-anio").values("id", "anio")),
        "periodos_academicos": list(PeriodoAcademico.objects.order_by("-anio_academico__anio", "fecha_inicio").values("id", "nombre", "anio_academico_id")),
        "grados": list(Grado.objects.filter(estado=1).order_by("nombre").values("id", "nombre")),
        "secciones": list(Seccion.objects.filter(estado=1).order_by("grado__nombre", "nombre").values("id", "nombre", "grado_id", "grado__nombre")),
        "docentes": _docentes_opciones(Docente.objects.filter(perfil__user__is_active=True)),
        "asignaciones_curso": _serializar_asignaciones(asignaciones, limite=None),
    }


def _opciones_asignaciones(asignaciones):
    anio_ids = asignaciones.values_list("anio_academico_id", flat=True).distinct()
    return {
        "anios_academicos": list(AnioAcademico.objects.filter(id__in=anio_ids).order_by("-anio").values("id", "anio")),
        "periodos_academicos": list(PeriodoAcademico.objects.filter(anio_academico_id__in=anio_ids).order_by("fecha_inicio").values("id", "nombre", "anio_academico_id")),
        "asignaciones_curso": _serializar_asignaciones(asignaciones, limite=None),
    }


def _opciones_apoderado(estudiantes):
    opciones = []
    for estudiante in estudiantes.select_related("perfil__user").distinct():
        user = estudiante.perfil.user
        opciones.append({"id": estudiante.id, "nombre": user.get_full_name().strip() or user.username})
    anio_ids = Matricula.objects.filter(estudiante__in=estudiantes).values_list("anio_academico_id", flat=True)
    return {
        "estudiantes": opciones,
        "anios_academicos": list(AnioAcademico.objects.filter(id__in=anio_ids).order_by("-anio").values("id", "anio")),
        "periodos_academicos": list(PeriodoAcademico.objects.filter(anio_academico_id__in=anio_ids).order_by("fecha_inicio").values("id", "nombre", "anio_academico_id")),
    }


def _serializar_asignaciones(asignaciones, limite=10):
    queryset = asignaciones.select_related("curso", "seccion__grado", "anio_academico").order_by("curso__nombre")
    if limite is not None:
        queryset = queryset[:limite]
    return [
        {
            "id": item.id,
            "curso": item.curso.nombre,
            "seccion": item.seccion.nombre,
            "grado": item.seccion.grado.nombre,
            "anio": item.anio_academico.anio,
        }
        for item in queryset
    ]


def _serializar_matriculas(matriculas):
    resultado = []
    for item in matriculas.select_related("estudiante__perfil__user", "seccion__grado", "anio_academico")[:10]:
        user = item.estudiante.perfil.user
        resultado.append(
            {
                "id": item.id,
                "estudiante_id": item.estudiante_id,
                "estudiante": user.get_full_name().strip() or user.username,
                "grado": item.seccion.grado.nombre,
                "seccion": item.seccion.nombre,
                "anio": item.anio_academico.anio,
                "estado": item.estado,
            }
        )
    return resultado


def _docentes_opciones(queryset):
    resultado = []
    for docente in queryset.select_related("perfil__user").order_by("perfil__user__last_name"):
        user = docente.perfil.user
        resultado.append({"id": docente.id, "nombre": user.get_full_name().strip() or user.username})
    return resultado


def _seguimiento_por_docente(registros):
    filas = defaultdict(lambda: {"observaciones": 0, "incidencias": 0, "recomendaciones": 0})
    nombres = {}
    for item in registros["observaciones"].values("docente_id", "docente__perfil__user__first_name", "docente__perfil__user__last_name").annotate(total=Count("id")):
        docente_id = item["docente_id"]
        nombres[docente_id] = _nombre_fila(item, "docente__perfil__user")
        filas[docente_id]["observaciones"] = item["total"]
    for item in registros["incidencias"].exclude(observacion__docente_id=None).values("observacion__docente_id", "observacion__docente__perfil__user__first_name", "observacion__docente__perfil__user__last_name").annotate(total=Count("id")):
        docente_id = item["observacion__docente_id"]
        nombres[docente_id] = _nombre_fila(item, "observacion__docente__perfil__user")
        filas[docente_id]["incidencias"] = item["total"]
    for item in registros["recomendaciones"].exclude(asignacion_curso__docente_id=None).values("asignacion_curso__docente_id", "asignacion_curso__docente__perfil__user__first_name", "asignacion_curso__docente__perfil__user__last_name").annotate(total=Count("id")):
        docente_id = item["asignacion_curso__docente_id"]
        nombres[docente_id] = _nombre_fila(item, "asignacion_curso__docente__perfil__user")
        filas[docente_id]["recomendaciones"] = item["total"]
    return [{"docente_id": key, "docente": nombres.get(key, "Sin nombre"), **value} for key, value in filas.items()]


def _nombre_fila(fila, prefijo):
    return " ".join(filter(None, (fila.get(f"{prefijo}__first_name"), fila.get(f"{prefijo}__last_name")))).strip() or "Sin nombre"


def _conteos_choices(queryset, campo, valores):
    resultado = {valor: 0 for valor in valores}
    for fila in queryset.values(campo).annotate(total=Count("id")):
        if fila[campo] in resultado:
            resultado[fila[campo]] = fila["total"]
    return resultado


def _datos_choices(conteos, choices):
    etiquetas = dict(choices)
    return [{"codigo": codigo, "etiqueta": etiquetas[codigo], "valor": conteos.get(codigo, 0)} for codigo, _ in choices]


def _distribucion(queryset, campo, choices):
    return _datos_choices(_conteos_choices(queryset, campo, [item[0] for item in choices]), choices)


def _agrupar(queryset, campo):
    return [
        {"etiqueta": fila[campo] or "Sin especificar", "valor": fila["total"]}
        for fila in queryset.values(campo).annotate(total=Count("id")).order_by(campo)
    ]


def _indicador(codigo, titulo, valor, unidad, interpretacion, estado):
    return {
        "codigo": codigo,
        "titulo": titulo,
        "valor": valor,
        "unidad": unidad,
        "interpretacion": interpretacion,
        "estado": estado,
    }


def _estado_asistencia(metricas):
    if not metricas["total_asistencias"]:
        return "sin_datos"
    if metricas["porcentaje_asistencia"] < UMBRAL_ASISTENCIA_ALERTA:
        return "alerta"
    return "bien"


def _porcentaje(parte, total):
    return round((parte * 100 / total), 1) if total else 0.0
