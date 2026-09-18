# Flujos academicos por rol

El SGA centraliza evidencias para detectar dificultades y comunicar acciones de apoyo de manera oportuna. Registrar una evidencia no equivale a enviar una notificacion. El docente revisa el contexto y decide cuando una comunicacion aporta al seguimiento.

| Modulo | Docente | Administracion o Directivo | Estudiante | Apoderado | Notificacion |
| --- | --- | --- | --- | --- | --- |
| Asistencia | Registra y corrige en sus cursos | Supervisa indicadores | Consulta la propia | Consulta la de sus estudiantes | Resumen opcional enviado por el docente |
| Calificaciones | Registra AD, A, B o C | Supervisa resultados | Consulta las propias | Consulta las de sus estudiantes | Resumen opcional enviado por el docente |
| Participaciones | Registra evidencias del curso | Consulta indicadores | Consulta las propias | Consulta el resumen en seguimiento | Se comunica solo si aporta al acompanamiento |
| Observaciones | Registra observaciones de sus estudiantes | Supervisa por docente | Consulta las observaciones del flujo actual | Consulta las de sus estudiantes | Puede formar parte de un resumen de seguimiento |
| Incidencias | Registra y realiza seguimiento | Supervisa abiertas y cerradas | Consulta las relacionadas con su matricula | Consulta las de sus estudiantes | El docente puede comunicar una incidencia concreta |
| Acciones de seguimiento | Crea, actualiza y cierra acciones | Supervisa cumplimiento | Consulta y reporta avances propios | Consulta y registra acompanamiento familiar | Se notifica al crear cuando el docente lo solicita |
| Recomendaciones IA | Genera, revisa, aprueba, edita, rechaza y publica | Supervisa la trazabilidad | Consulta solo aprobadas o editadas | Consulta solo aprobadas o editadas | Al publicar se notifica al estudiante y, opcionalmente, a apoderados |
| Reportes | Consulta reportes de sus cursos | Consulta reportes institucionales | Consulta sus modulos personales | Consulta la informacion de sus estudiantes | No genera notificaciones automaticamente |

## Publicacion de una recomendacion IA

1. El docente genera la recomendacion. Queda en `PENDIENTE` y no produce notificaciones.
2. El docente revisa el contenido y lo marca como `APROBADA`, `EDITADA` o `RECHAZADA`.
3. Solo una recomendacion `APROBADA` o `EDITADA` puede publicarse.
4. La publicacion siempre puede dirigirse al estudiante y puede incluir a sus apoderados.
5. Se crea una alerta interna por destinatario y se intenta enviar su correo.
6. Un fallo de correo no elimina la alerta interna.
7. La misma recomendacion no se notifica dos veces al mismo usuario.

```text
POST /api/docente/recomendaciones-ia/{recomendacion_id}/publicar/
```

```json
{
  "notificar_estudiante": true,
  "notificar_apoderados": true,
  "prioridad": "ALTA",
  "mensaje_adicional": "Revisaremos los avances la proxima semana."
}
```

## Comunicaciones academicas

El docente puede preparar y enviar resumenes reales de asistencia, calificaciones, incidencia, seguimiento o una recomendacion aprobada. Cada correo genera tambien una notificacion en la bandeja del apoderado.

```text
POST /api/docente/comunicaciones/previsualizar/
POST /api/docente/comunicaciones/enviar/
GET  /api/docente/comunicaciones/
```

La previsualizacion no persiste ni envia informacion. Si el apoderado no tiene email, recibira la alerta interna y el intento de correo quedara como fallido. Los usuarios inactivos se omiten.
