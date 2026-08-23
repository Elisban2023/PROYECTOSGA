# Recomendaciones pedagogicas con IA

La generacion es una accion explicita del docente. Listar estudiantes,
seguimiento o dashboards no consume la API de OpenAI.

## Configuracion

Definir en .env:

    OPENAI_ENABLED=True
    OPENAI_API_KEY=sk-proj-...
    OPENAI_MODEL=gpt-5.2
    OPENAI_API_URL=https://api.openai.com/v1/responses
    OPENAI_TIMEOUT=45
    OPENAI_MAX_OUTPUT_TOKENS=1200

La clave nunca debe enviarse al frontend ni guardarse en Git.

## Endpoints del docente

Todas las rutas requieren JWT con rol Docente.

- GET /api/docente/recomendaciones-ia/
- GET /api/docente/recomendaciones-ia/{id}/
- POST /api/docente/recomendaciones-ia/generar/
- PATCH /api/docente/recomendaciones-ia/{id}/revisar/

Filtros del listado: asignacion_curso, matricula, periodo_academico y
estado_revision.

Generacion:

    {
      "matricula": 26,
      "asignacion_curso": 20,
      "periodo_academico": 8
    }

Revision:

    {
      "estado_revision": "EDITADA",
      "texto_revisado": "Texto revisado por el docente antes de compartir."
    }

Los estados permitidos son APROBADA, RECHAZADA y EDITADA. Las
recomendaciones solo son visibles para estudiantes y apoderados cuando
estan APROBADA o EDITADA.

Errores de configuracion, cuota, timeout o indisponibilidad de OpenAI se
devuelven como 503 sin incluir credenciales ni el cuerpo privado del proveedor.
