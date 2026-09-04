from collections import Counter

from django.conf import settings
from rest_framework.exceptions import ValidationError

from sga.models import (
    Asistencia,
    Calificacion,
    CorreoInstitucional,
    EstadoMatricula,
    EstadoRevisionIA,
    IncidenciaAcademica,
    Matricula,
    ObservacionAcademica,
    PeriodoAcademico,
    RecomendacionIA,
    TipoCorreo,
    VinculoApoderado,
)
from sga.roles import ROLE_APODERADO
from sga.services.correos import CorreoError, enviar_correo_institucional, renderizar_correo
from sga.services.docente import get_asignaciones_docente
from sga.services.recomendaciones_docente import ESTADOS_PUBLICADOS, parsear_contenido_generado


def preparar_comunicacion_docente(user, datos):
    asignacion = get_asignaciones_docente(user).filter(pk=datos["asignacion_curso_id"]).first()
    if asignacion is None:
        raise ValidationError(
            {"asignacion_curso_id": "No tiene una asignacion activa con ese identificador."}
        )

    matricula = (
        Matricula.objects.filter(
            pk=datos["matricula_id"],
            seccion_id=asignacion.seccion_id,
            anio_academico_id=asignacion.anio_academico_id,
            estado=EstadoMatricula.ACTIVA,
        )
        .select_related("estudiante__perfil__user", "seccion__grado", "anio_academico")
        .first()
    )
    if matricula is None:
        raise ValidationError(
            {"matricula_id": "La matricula no pertenece a la seccion y anio del curso."}
        )

    periodo = _obtener_periodo(matricula, datos.get("periodo_academico_id"))
    tipo = datos["tipo"]
    asunto, mensaje, origen = _construir_contenido(
        tipo=tipo,
        matricula=matricula,
        asignacion=asignacion,
        periodo=periodo,
        recomendacion_id=datos.get("recomendacion_id"),
        incidencia_id=datos.get("incidencia_id"),
    )
    adicional = (datos.get("mensaje_adicional") or "").strip()
    if adicional:
        mensaje += f"\n\nMensaje adicional del docente:\n{adicional}"

    ruta, accion_texto = _accion_frontend(tipo, matricula.estudiante_id)
    vinculos = list(
        VinculoApoderado.objects.filter(estudiante=matricula.estudiante)
        .select_related("apoderado__perfil__user")
        .order_by("-es_principal", "id")
    )
    if not vinculos:
        raise ValidationError(
            {"matricula_id": "El estudiante no tiene apoderados vinculados."}
        )

    destinatarios = []
    omitidos = []
    for vinculo in vinculos:
        usuario = vinculo.apoderado.perfil.user
        if usuario.is_active and usuario.email:
            destinatarios.append(usuario)
        else:
            omitidos.append(
                {
                    "apoderado_id": vinculo.apoderado_id,
                    "nombre": usuario.get_full_name().strip() or usuario.username,
                    "motivo": "Usuario inactivo o sin correo electronico.",
                }
            )
    if not destinatarios:
        raise ValidationError(
            {"matricula_id": "Ningun apoderado vinculado tiene un correo habilitado."}
        )

    return {
        "tipo": tipo,
        "matricula": matricula,
        "asignacion_curso": asignacion,
        "periodo_academico": periodo,
        "recomendacion": origen if isinstance(origen, RecomendacionIA) else None,
        "incidencia": origen if isinstance(origen, IncidenciaAcademica) else None,
        "asunto": asunto,
        "mensaje": mensaje,
        "accion_texto": accion_texto,
        "accion_url": f"{settings.FRONTEND_URL}{ruta}",
        "destinatarios": destinatarios,
        "omitidos": omitidos,
    }


def previsualizar_comunicacion_docente(user, datos):
    comunicacion = preparar_comunicacion_docente(user, datos)
    contenido = renderizar_correo(
        destinatario=comunicacion["destinatarios"][0],
        rol=ROLE_APODERADO,
        asunto=comunicacion["asunto"],
        mensaje=comunicacion["mensaje"],
        accion_texto=comunicacion["accion_texto"],
        accion_url=comunicacion["accion_url"],
    )
    return comunicacion, contenido


def enviar_comunicacion_docente(user, datos):
    comunicacion = preparar_comunicacion_docente(user, datos)
    enviados = []
    fallidos = []
    campos = {
        clave: valor
        for clave, valor in comunicacion.items()
        if clave
        in {
            "tipo",
            "matricula",
            "asignacion_curso",
            "periodo_academico",
            "recomendacion",
            "incidencia",
            "asunto",
            "mensaje",
            "accion_texto",
            "accion_url",
        }
    }
    for destinatario in comunicacion["destinatarios"]:
        try:
            correo = enviar_correo_institucional(
                destinatario=destinatario,
                enviado_por=user,
                rol=ROLE_APODERADO,
                **campos,
            )
            enviados.append(correo)
        except CorreoError as exc:
            fallidos.append(exc.correo)
    return comunicacion, enviados, fallidos


def get_comunicaciones_docente(user):
    return CorreoInstitucional.objects.filter(
        enviado_por=user,
        tipo__in=(
            TipoCorreo.CALIFICACIONES,
            TipoCorreo.RECOMENDACION,
            TipoCorreo.INCIDENCIA,
            TipoCorreo.ASISTENCIA,
            TipoCorreo.SEGUIMIENTO,
        ),
    ).select_related(
        "destinatario",
        "enviado_por",
        "matricula__estudiante__perfil__user",
        "asignacion_curso__curso",
        "periodo_academico",
        "recomendacion",
        "incidencia",
    )


def _obtener_periodo(matricula, periodo_id):
    if periodo_id is None:
        return None
    periodo = PeriodoAcademico.objects.filter(
        pk=periodo_id,
        anio_academico_id=matricula.anio_academico_id,
    ).first()
    if periodo is None:
        raise ValidationError(
            {"periodo_academico_id": "El periodo no pertenece al anio de la matricula."}
        )
    return periodo


def _construir_contenido(*, tipo, matricula, asignacion, periodo, recomendacion_id, incidencia_id):
    estudiante = matricula.estudiante.perfil.user
    nombre = estudiante.get_full_name().strip() or estudiante.username
    curso = asignacion.curso.nombre
    contexto = f"Estudiante: {nombre}\nCurso: {curso}\nGrado y seccion: {matricula.seccion}"
    if periodo:
        contexto += f"\nPeriodo: {periodo.nombre}"

    if tipo == TipoCorreo.CALIFICACIONES:
        registros = Calificacion.objects.filter(matricula=matricula, asignacion_curso=asignacion)
        if periodo:
            registros = registros.filter(periodo_academico=periodo)
        registros = list(registros.select_related("criterio_calificacion").order_by("criterio_calificacion__nombre"))
        if not registros:
            raise ValidationError({"tipo": "No existen calificaciones para comunicar con esos filtros."})
        detalle = "\n".join(
            f"- {registro.criterio_calificacion.nombre}: {registro.get_valor_display()} ({registro.valor})"
            for registro in registros
        )
        return f"Calificaciones de {nombre}", f"{contexto}\n\nCalificaciones registradas:\n{detalle}", None

    if tipo == TipoCorreo.RECOMENDACION:
        recomendacion = RecomendacionIA.objects.filter(
            pk=recomendacion_id,
            matricula=matricula,
            asignacion_curso=asignacion,
            estado_revision__in=ESTADOS_PUBLICADOS,
            activo=True,
        ).first()
        if recomendacion is None:
            raise ValidationError(
                {"recomendacion_id": "La recomendacion no existe, no pertenece al curso o no esta aprobada."}
            )
        texto = recomendacion.texto_revisado or _recomendacion_a_texto(recomendacion.texto_generado)
        return f"Recomendacion pedagogica para {nombre}", f"{contexto}\n\nRecomendacion revisada por el docente:\n{texto}", recomendacion

    if tipo == TipoCorreo.INCIDENCIA:
        incidencia = IncidenciaAcademica.objects.filter(
            pk=incidencia_id,
            matricula=matricula,
            observacion__asignacion_curso=asignacion,
            observacion__docente=asignacion.docente,
        ).first()
        if incidencia is None:
            raise ValidationError(
                {"incidencia_id": "La incidencia no existe o no corresponde al curso del docente."}
            )
        detalle = (
            f"Tipo: {incidencia.get_tipo_display()}\n"
            f"Nivel: {incidencia.get_nivel_display() if incidencia.nivel else 'No especificado'}\n"
            f"Estado: {incidencia.get_estado_display()}\n"
            f"Descripcion: {incidencia.descripcion}"
        )
        return f"Comunicacion de incidencia de {nombre}", f"{contexto}\n\n{detalle}", incidencia

    if tipo == TipoCorreo.ASISTENCIA:
        registros = Asistencia.objects.filter(matricula=matricula, asignacion_curso=asignacion)
        if periodo:
            registros = registros.filter(fecha__range=(periodo.fecha_inicio, periodo.fecha_fin))
        estados = Counter(registros.values_list("estado", flat=True))
        if not estados:
            raise ValidationError({"tipo": "No existen asistencias para comunicar con esos filtros."})
        detalle = "\n".join(f"- {estado.title()}: {total}" for estado, total in sorted(estados.items()))
        return f"Resumen de asistencia de {nombre}", f"{contexto}\n\nAsistencias registradas:\n{detalle}", None

    observaciones = ObservacionAcademica.objects.filter(
        matricula=matricula,
        asignacion_curso=asignacion,
        docente=asignacion.docente,
        activo=True,
    ).order_by("-fecha")[:5]
    incidencias = IncidenciaAcademica.objects.filter(
        matricula=matricula,
        observacion__asignacion_curso=asignacion,
        observacion__docente=asignacion.docente,
    ).order_by("-fecha_registro")[:5]
    lineas = [f"- Observacion ({item.categoria}): {item.descripcion}" for item in observaciones]
    lineas += [f"- Incidencia ({item.get_estado_display()}): {item.descripcion}" for item in incidencias]
    if not lineas:
        raise ValidationError({"tipo": "No existen registros de seguimiento para comunicar."})
    return f"Seguimiento academico de {nombre}", f"{contexto}\n\nResumen de seguimiento:\n" + "\n".join(lineas), None


def _recomendacion_a_texto(texto_generado):
    contenido = parsear_contenido_generado(texto_generado)
    partes = [contenido.get("resumen", "")]
    for titulo, clave in (
        ("Fortalezas", "fortalezas"),
        ("Aspectos por reforzar", "aspectos_reforzar"),
        ("Acciones sugeridas para el estudiante", "acciones_estudiante"),
        ("Comunicacion sugerida", "comunicacion_apoderado"),
    ):
        valor = contenido.get(clave)
        if isinstance(valor, list):
            valor = "; ".join(valor)
        if valor:
            partes.append(f"{titulo}: {valor}")
    return "\n\n".join(parte for parte in partes if parte)


def _accion_frontend(tipo, estudiante_id):
    rutas = {
        TipoCorreo.CALIFICACIONES: ("/apoderado/calificaciones", "Ver calificaciones"),
        TipoCorreo.RECOMENDACION: ("/apoderado/seguimiento", "Ver seguimiento"),
        TipoCorreo.INCIDENCIA: ("/apoderado/seguimiento", "Ver seguimiento"),
        TipoCorreo.ASISTENCIA: ("/apoderado/asistencia", "Ver asistencia"),
        TipoCorreo.SEGUIMIENTO: ("/apoderado/seguimiento", "Ver seguimiento"),
    }
    ruta, texto = rutas[tipo]
    return f"{ruta}?estudiante={estudiante_id}", texto
