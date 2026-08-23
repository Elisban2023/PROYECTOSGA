import json
import socket
from urllib import error, request

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from sga.models import (
    Asistencia,
    Calificacion,
    EstadoAcademico,
    EstadoMatricula,
    EstadoRevisionIA,
    IncidenciaAcademica,
    Matricula,
    ObservacionAcademica,
    Participacion,
    PeriodoAcademico,
    RecomendacionIA,
)
from sga.services.docente import get_asignaciones_docente


ESTADOS_PUBLICADOS = (EstadoRevisionIA.APROBADA, EstadoRevisionIA.EDITADA)
SECCIONES_RECOMENDACION = (
    "resumen",
    "fortalezas",
    "aspectos_reforzar",
    "acciones_docente",
    "acciones_estudiante",
    "comunicacion_apoderado",
)

RECOMENDACION_SCHEMA = {
    "type": "object",
    "properties": {
        "resumen": {"type": "string"},
        "fortalezas": {"type": "array", "items": {"type": "string"}},
        "aspectos_reforzar": {"type": "array", "items": {"type": "string"}},
        "acciones_docente": {"type": "array", "items": {"type": "string"}},
        "acciones_estudiante": {"type": "array", "items": {"type": "string"}},
        "comunicacion_apoderado": {"type": "string"},
    },
    "required": list(SECCIONES_RECOMENDACION),
    "additionalProperties": False,
}


class ServicioIAError(APIException):
    status_code = 503
    default_detail = "El servicio de IA no esta disponible en este momento."


def get_recomendaciones_docente(
    user,
    *,
    asignacion_curso=None,
    matricula=None,
    periodo_academico=None,
    estado_revision=None,
):
    docente = user.perfil.docente
    queryset = (
        RecomendacionIA.objects.filter(
            asignacion_curso__docente=docente,
            activo=True,
        )
        .select_related(
            "matricula__estudiante__perfil__user",
            "matricula__seccion__grado",
            "asignacion_curso__curso",
            "asignacion_curso__seccion__grado",
            "periodo_academico",
            "revisado_por_docente__perfil__user",
        )
        .order_by("-fecha_generacion")
    )
    filtros = {
        "asignacion_curso_id": asignacion_curso,
        "matricula_id": matricula,
        "periodo_academico_id": periodo_academico,
        "estado_revision": estado_revision,
    }
    for campo, valor in filtros.items():
        if valor is not None:
            queryset = queryset.filter(**{campo: valor})
    return queryset


def get_recomendacion_docente(user, recomendacion_id):
    recomendacion = get_recomendaciones_docente(user).filter(pk=recomendacion_id).first()
    if recomendacion is None:
        raise NotFound(
            "La recomendacion no existe o no pertenece a sus cursos."
        )
    return recomendacion


def generar_recomendacion_docente(
    user,
    *,
    matricula,
    asignacion_curso,
    periodo_academico=None,
):
    if not settings.OPENAI_ENABLED:
        raise ServicioIAError("El servicio de IA esta deshabilitado.")
    if not settings.OPENAI_API_KEY:
        raise ServicioIAError("OPENAI_API_KEY no esta configurada.")

    contexto, asignacion, matricula_obj, periodo = _construir_contexto(
        user,
        matricula_id=matricula,
        asignacion_id=asignacion_curso,
        periodo_id=periodo_academico,
    )
    contenido = _solicitar_recomendacion_openai(contexto)
    return RecomendacionIA.objects.create(
        matricula=matricula_obj,
        asignacion_curso=asignacion,
        periodo_academico=periodo,
        resumen_contexto=json.dumps(contexto, ensure_ascii=False, default=str),
        texto_generado=json.dumps(contenido, ensure_ascii=False),
        estado_revision=EstadoRevisionIA.PENDIENTE,
        fecha_generacion=timezone.now(),
    )


def revisar_recomendacion_docente(
    user,
    *,
    recomendacion_id,
    estado_revision,
    texto_revisado=None,
):
    recomendacion = get_recomendacion_docente(user, recomendacion_id)
    texto = (texto_revisado or "").strip() or None
    if estado_revision == EstadoRevisionIA.EDITADA and not texto:
        raise ValidationError(
            {"texto_revisado": "Debe registrar el texto revisado para marcarla como editada."}
        )
    if estado_revision == EstadoRevisionIA.RECHAZADA:
        texto = None
    recomendacion.registrar_revision(
        docente=user.perfil.docente,
        estado_revision=estado_revision,
        texto_revisado=texto,
    )
    return recomendacion


def get_recomendaciones_publicadas(matricula):
    recomendaciones = (
        RecomendacionIA.objects.filter(
            matricula=matricula,
            activo=True,
            estado_revision__in=ESTADOS_PUBLICADOS,
        )
        .select_related("asignacion_curso__curso", "periodo_academico")
        .order_by("-fecha_revision", "-fecha_generacion")
    )
    return [
        {
            "id": recomendacion.id,
            "curso_nombre": (
                recomendacion.asignacion_curso.curso.nombre
                if recomendacion.asignacion_curso
                else None
            ),
            "periodo_nombre": (
                recomendacion.periodo_academico.nombre
                if recomendacion.periodo_academico
                else None
            ),
            "texto": recomendacion.texto_revisado
            or _contenido_a_texto(recomendacion.texto_generado),
            "estado_revision": recomendacion.estado_revision,
            "fecha_revision": recomendacion.fecha_revision,
        }
        for recomendacion in recomendaciones
    ]


def parsear_contenido_generado(texto):
    try:
        contenido = json.loads(texto)
    except (TypeError, json.JSONDecodeError):
        return {
            "resumen": (texto or "").strip(),
            "fortalezas": [],
            "aspectos_reforzar": [],
            "acciones_docente": [],
            "acciones_estudiante": [],
            "comunicacion_apoderado": "",
        }
    return contenido if isinstance(contenido, dict) else {}


def _construir_contexto(user, *, matricula_id, asignacion_id, periodo_id):
    asignacion = get_asignaciones_docente(user).filter(pk=asignacion_id).first()
    if asignacion is None:
        raise ValidationError(
            {"asignacion_curso": "No tiene una asignacion activa con ese identificador."}
        )
    matricula = (
        Matricula.objects.filter(
            pk=matricula_id,
            seccion_id=asignacion.seccion_id,
            anio_academico_id=asignacion.anio_academico_id,
            estado=EstadoMatricula.ACTIVA,
        )
        .select_related("estudiante", "seccion__grado", "anio_academico")
        .first()
    )
    if matricula is None:
        raise ValidationError(
            {"matricula": "La matricula no pertenece a la seccion y anio del curso."}
        )

    periodo = None
    if periodo_id is not None:
        periodo = PeriodoAcademico.objects.filter(
            pk=periodo_id,
            anio_academico_id=matricula.anio_academico_id,
        ).first()
        if periodo is None or periodo.estado == EstadoAcademico.INACTIVO:
            raise ValidationError(
                {"periodo_academico": "El periodo no pertenece al anio o esta inactivo."}
            )

    asistencias = Asistencia.objects.filter(
        matricula=matricula,
        asignacion_curso=asignacion,
    )
    calificaciones = Calificacion.objects.filter(
        matricula=matricula,
        asignacion_curso=asignacion,
    )
    participaciones = Participacion.objects.filter(
        matricula=matricula,
        asignacion_curso=asignacion,
    )
    observaciones = ObservacionAcademica.objects.filter(
        matricula=matricula,
        asignacion_curso=asignacion,
        docente=asignacion.docente,
        activo=True,
    )
    incidencias = IncidenciaAcademica.objects.filter(
        matricula=matricula,
        observacion__asignacion_curso=asignacion,
        observacion__docente=asignacion.docente,
    )
    if periodo is not None:
        asistencias = asistencias.filter(
            fecha__range=(periodo.fecha_inicio, periodo.fecha_fin)
        )
        calificaciones = calificaciones.filter(periodo_academico=periodo)
        participaciones = participaciones.filter(periodo_academico=periodo)
        observaciones = observaciones.filter(
            fecha__date__range=(periodo.fecha_inicio, periodo.fecha_fin)
        )
        incidencias = incidencias.filter(
            fecha_registro__date__range=(periodo.fecha_inicio, periodo.fecha_fin)
        )

    asistencia_por_estado = {
        fila["estado"]: fila["total"]
        for fila in asistencias.values("estado").annotate(total=Count("id"))
    }
    return (
        {
            "estudiante": {
                "codigo": matricula.estudiante.codigo_estudiante,
                "grado": matricula.seccion.grado.nombre,
                "seccion": matricula.seccion.nombre,
                "anio_academico": matricula.anio_academico.anio,
            },
            "curso": {
                "nombre": asignacion.curso.nombre,
                "periodo": periodo.nombre if periodo else "Todos los periodos disponibles",
            },
            "asistencia": {
                "total": asistencias.count(),
                "por_estado": asistencia_por_estado,
            },
            "calificaciones": list(
                calificaciones.order_by("-id").values(
                    "valor",
                    "observacion",
                    "criterio_calificacion__nombre",
                    "criterio_calificacion__capacidad__nombre",
                    "criterio_calificacion__capacidad__competencia__nombre",
                )[:20]
            ),
            "participaciones": list(
                participaciones.order_by("-fecha").values(
                    "fecha", "tipo", "valor", "observacion"
                )[:15]
            ),
            "observaciones": list(
                observaciones.order_by("-fecha").values(
                    "fecha", "categoria", "descripcion"
                )[:15]
            ),
            "incidencias": list(
                incidencias.order_by("-fecha_registro").values(
                    "fecha_registro", "tipo", "nivel", "estado", "descripcion"
                )[:10]
            ),
        },
        asignacion,
        matricula,
        periodo,
    )


def _solicitar_recomendacion_openai(contexto):
    instrucciones = (
        "Eres un asistente pedagogico para educacion secundaria peruana. "
        "Genera una recomendacion clara, respetuosa y accionable usando solo los "
        "datos del contexto. No inventes hechos, diagnosticos, causas ni datos "
        "familiares. Si no hay evidencia para una seccion, indicalo brevemente. "
        "Las acciones deben ser concretas y apropiadas para el aula. La comunicacion "
        "al apoderado debe sugerirse solo cuando aporte al seguimiento."
    )
    payload = {
        "model": settings.OPENAI_MODEL,
        "instructions": instrucciones,
        "input": json.dumps(contexto, ensure_ascii=False, default=str),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "recomendacion_pedagogica",
                "strict": True,
                "schema": RECOMENDACION_SCHEMA,
            }
        },
        "max_output_tokens": settings.OPENAI_MAX_OUTPUT_TOKENS,
        "store": False,
    }
    api_request = request.Request(
        settings.OPENAI_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(api_request, timeout=settings.OPENAI_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise ServicioIAError(_mensaje_error_openai(exc)) from exc
    except (error.URLError, TimeoutError, socket.timeout) as exc:
        raise ServicioIAError(
            "No se pudo conectar con OpenAI o se agoto el tiempo de espera."
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ServicioIAError("OpenAI devolvio una respuesta que no pudo procesarse.") from exc

    texto = _extraer_output_text(data)
    try:
        contenido = json.loads(texto)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ServicioIAError("OpenAI no devolvio una recomendacion JSON valida.") from exc
    _validar_contenido(contenido)
    return contenido


def _extraer_output_text(data):
    texto = (data.get("output_text") or "").strip()
    if texto:
        return texto
    for salida in data.get("output", []):
        for contenido in salida.get("content", []):
            if contenido.get("type") == "output_text":
                texto = (contenido.get("text") or "").strip()
                if texto:
                    return texto
    raise ServicioIAError("OpenAI no devolvio una recomendacion.")


def _validar_contenido(contenido):
    if not isinstance(contenido, dict):
        raise ServicioIAError("OpenAI devolvio una recomendacion con formato invalido.")
    for seccion in SECCIONES_RECOMENDACION:
        if seccion not in contenido:
            raise ServicioIAError("OpenAI devolvio una recomendacion incompleta.")
    if not isinstance(contenido["resumen"], str) or not isinstance(
        contenido["comunicacion_apoderado"],
        str,
    ):
        raise ServicioIAError("OpenAI devolvio una recomendacion con formato invalido.")
    for seccion in (
        "fortalezas",
        "aspectos_reforzar",
        "acciones_docente",
        "acciones_estudiante",
    ):
        if not isinstance(contenido[seccion], list) or not all(
            isinstance(elemento, str) for elemento in contenido[seccion]
        ):
            raise ServicioIAError("OpenAI devolvio una recomendacion con formato invalido.")


def _mensaje_error_openai(exc):
    codigo = exc.code
    tipo = ""
    try:
        cuerpo = json.loads(exc.read().decode("utf-8"))
        tipo = cuerpo.get("error", {}).get("type", "")
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    if codigo == 401:
        return "OpenAI rechazo las credenciales configuradas."
    if codigo == 429 or tipo == "insufficient_quota":
        return "OpenAI no tiene cuota disponible o alcanzo su limite de uso."
    if codigo in (400, 404):
        return "OpenAI rechazo la configuracion del modelo o la solicitud."
    if codigo >= 500:
        return "OpenAI no esta disponible temporalmente."
    return "OpenAI no pudo generar la recomendacion."


def _contenido_a_texto(texto_generado):
    contenido = parsear_contenido_generado(texto_generado)
    partes = [contenido.get("resumen", "")]
    for titulo, clave in (
        ("Fortalezas", "fortalezas"),
        ("Aspectos por reforzar", "aspectos_reforzar"),
        ("Acciones para el docente", "acciones_docente"),
        ("Acciones para el estudiante", "acciones_estudiante"),
    ):
        elementos = contenido.get(clave) or []
        if elementos:
            partes.append(f"{titulo}: " + "; ".join(elementos))
    comunicacion = contenido.get("comunicacion_apoderado")
    if comunicacion:
        partes.append("Comunicacion con el apoderado: " + comunicacion)
    return "\n\n".join(parte for parte in partes if parte)
