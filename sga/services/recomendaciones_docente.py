import json
from urllib import error, request

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from sga.models import EstadoRevisionIA, RecomendacionIA
from sga.services.seguimiento_docente import get_detalle_seguimiento_docente


class ServicioIAError(APIException):
    status_code = 503
    default_detail = "El servicio de IA no esta disponible en este momento."


def get_recomendaciones_docente(user):
    docente = user.perfil.docente
    asignacion_ids = docente.asignaciones_curso.filter(estado=1).values_list("id", flat=True)
    return RecomendacionIA.objects.filter(
        matricula__observaciones_academicas__asignacion_curso_id__in=asignacion_ids,
        activo=True,
    ).distinct().select_related("matricula__estudiante__perfil__user", "periodo_academico").order_by("-fecha_generacion")


def generar_recomendacion_docente(user, *, matricula_id, asignacion_curso, periodo_academico=None):
    detalle = get_detalle_seguimiento_docente(user, matricula_id=matricula_id, asignacion_curso=asignacion_curso)
    if not settings.OPENAI_ENABLED or not settings.OPENAI_API_KEY:
        raise ServicioIAError("OPENAI_API_KEY no esta configurada o el servicio esta deshabilitado.")
    contexto = json.dumps(detalle, ensure_ascii=False, default=str)
    prompt = (
        "Eres un asistente pedagogico para secundaria. Con base solo en este seguimiento "
        "del estudiante, redacta una recomendacion breve, respetuosa, accionable y sin diagnosticos. "
        "Incluye acciones para docente y estudiante. No inventes datos.\n\n"
        f"Seguimiento: {contexto}"
    )
    payload = json.dumps({
        "model": settings.OPENAI_MODEL,
        "input": prompt,
        "text": {"verbosity": "low"},
        "store": False,
    }).encode("utf-8")
    api_request = request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(api_request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise ServicioIAError("OpenAI no pudo generar la recomendacion. Verifique cuota y configuracion.") from exc
    except (error.URLError, TimeoutError) as exc:
        raise ServicioIAError("No se pudo conectar con OpenAI.") from exc
    texto = (data.get("output_text") or "").strip()
    if not texto:
        raise ServicioIAError("OpenAI no devolvio una recomendacion valida.")
    return RecomendacionIA.objects.create(
        matricula_id=matricula_id,
        periodo_academico_id=periodo_academico,
        resumen_contexto=contexto,
        texto_generado=texto,
        estado_revision=EstadoRevisionIA.PENDIENTE,
        fecha_generacion=timezone.now(),
    )
