# Notificaciones multirrol

## Flujo funcional

1. Solo un usuario con rol Docente crea la notificacion.
2. El backend valida que cada destinatario pertenezca al alcance academico del docente.
3. Se crea una notificacion interna independiente para cada destinatario.
4. Se intenta enviar inmediatamente un correo con el formato correspondiente al rol.
5. Si SendGrid falla, la notificacion interna se conserva y `estado_envio` queda en `FALLIDA`.
6. Cada usuario consulta exclusivamente su bandeja y marca sus propias notificaciones como leidas.
7. La creacion y las lecturas quedan registradas en auditoria.

Las comunicaciones academicas enviadas por el docente tambien crean una notificacion interna. La recomendacion IA se notifica unicamente despues de la revision humana, mediante una accion explicita de publicacion.

El frontend puede consultar novedades cada 20 segundos usando `desde_id`. Este mecanismo es compatible con el despliegue monolitico actual y no requiere WebSockets ni Redis.

## APIs comunes para todos los roles

- `GET /api/notificaciones/mias/`: bandeja personal.
- `GET /api/notificaciones/mias/resumen/`: contador para la campana.
- `POST /api/notificaciones/mias/{id}/marcar-leida/`: lectura individual.
- `POST /api/notificaciones/mias/marcar-todas-leidas/`: lectura masiva.

Filtros de bandeja:

- `solo_no_leidas=true`
- `tipo=INCIDENCIA`
- `prioridad=ALTA`
- `desde_id=125`
- `limite=30`

La bandeja devuelve `results` y `meta`, donde `meta.ultimo_id` sirve como cursor para solicitar solo notificaciones nuevas.

## APIs exclusivas para Docente

- `GET /api/docente/notificaciones/destinatarios/`
- `POST /api/docente/notificaciones/enviar/`
- `GET /api/docente/notificaciones/enviadas/`
- `POST /api/docente/recomendaciones-ia/{id}/publicar/`

El buscador de destinatarios acepta `rol`, `buscar` e `incidencia_id`. Nunca se debe construir el selector desde `/api/usuarios/`, porque esa ruta puede incluir usuarios fuera del alcance del docente.

Ejemplo de envio:

```json
{
  "destinatarios": [12, 18],
  "tipo": "INCIDENCIA",
  "prioridad": "ALTA",
  "titulo": "Seguimiento de asistencia",
  "mensaje": "Se registro una incidencia que requiere seguimiento oportuno.",
  "incidencia_id": 8,
  "accion_url": "/seguimiento/incidencias"
}
```

Tipos: `ACADEMICA`, `ASISTENCIA`, `CALIFICACION`, `INCIDENCIA`, `RECOMENDACION` e `INSTITUCIONAL`.

Prioridades: `BAJA`, `NORMAL`, `ALTA` y `URGENTE`.

## Alertas del navegador

El sonido, toast flotante y notificacion nativa se implementan en React al detectar elementos nuevos. Deben respetarse estas reglas:

- Solicitar permiso de notificaciones mediante una accion explicita del usuario.
- Usar notificaciones nativas solo cuando `Notification.permission === "granted"`.
- Reproducir sonido solo si el usuario lo habilito y el navegador ya registro una interaccion.
- Guardar preferencias de sonido y notificacion nativa por usuario.
- No incluir datos academicos sensibles en el titulo de una notificacion nativa; mostrar un resumen neutro cuando la pestana no esta activa.
- No volver a emitir sonido para IDs ya procesados.
- Las notificaciones `URGENTE` no deben eludir las preferencias ni las restricciones del navegador.

En desarrollo, las notificaciones nativas requieren un origen seguro. El tunel HTTPS cumple esta condicion; `localhost` puede recibir un tratamiento especial segun el navegador.
