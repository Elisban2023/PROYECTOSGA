# Acciones de seguimiento

El modulo convierte las evidencias academicas en un ciclo verificable de mejora:

1. El sistema presenta senales objetivas de asistencia, niveles de logro e incidencias.
2. El docente interpreta la informacion y crea una accion de apoyo.
3. La accion define responsable, prioridad, fecha limite y visibilidad.
4. El estudiante y el apoderado registran avances o evidencias cuando corresponda.
5. El docente revisa la linea de tiempo y cierra la accion registrando el resultado.
6. Administracion supervisa el cumplimiento sin modificar el trabajo pedagogico.

Las senales no son diagnosticos ni decisiones automatizadas. El docente mantiene la
responsabilidad de interpretar el contexto y decidir la intervencion pertinente.

## Endpoints

| Rol | Metodo y endpoint | Uso |
| --- | --- | --- |
| Docente | `GET/POST /api/docente/acciones-seguimiento/` | Lista o crea acciones de sus cursos |
| Docente | `GET/PATCH /api/docente/acciones-seguimiento/{id}/` | Consulta, edita o cierra una accion propia |
| Docente | `POST /api/docente/acciones-seguimiento/{id}/actualizaciones/` | Agrega comentarios, avances o evidencias |
| Estudiante | `GET /api/estudiante/acciones-seguimiento/` | Consulta solo acciones propias y visibles |
| Estudiante | `POST /api/estudiante/acciones-seguimiento/{id}/actualizaciones/` | Informa su avance |
| Apoderado | `GET /api/apoderado/acciones-seguimiento/?estudiante={id}` | Consulta acciones visibles de estudiantes vinculados |
| Apoderado | `POST /api/apoderado/acciones-seguimiento/{id}/actualizaciones/` | Registra acompanamiento o evidencia familiar |
| Administracion | `GET /api/administracion/acciones-seguimiento/` | Supervisa por docente, estado, prioridad o vencimiento |

Todos requieren JWT. Los listados aceptan `estado`, `prioridad`, `responsable`,
`periodo_academico`, `matricula`, `asignacion_curso` y `vencidas=true` segun el
alcance del rol. Administracion tambien puede filtrar por `docente`.

## Crear una accion

```json
{
  "matricula_id": 26,
  "asignacion_curso_id": 8,
  "periodo_academico_id": 3,
  "tipo": "REFUERZO",
  "responsable": "COMPARTIDA",
  "prioridad": "ALTA",
  "titulo": "Reforzar la sustentacion del proyecto",
  "descripcion": "Completar la propuesta y revisar los avances con el docente.",
  "fecha_limite": "2026-09-30",
  "visible_estudiante": true,
  "visible_apoderado": true,
  "notificar_destinatarios": true
}
```

La accion puede vincular opcionalmente `incidencia_id` o `recomendacion_id`. La
recomendacion debe estar revisada y la incidencia no puede estar cerrada. Si se
solicita notificacion, se crea una alerta interna y se intenta enviar correo; un
fallo de correo no elimina la accion ni la alerta.

## Registrar avance y cerrar

```json
{
  "tipo": "AVANCE",
  "comentario": "Complete la primera parte y adjunto la evidencia descrita.",
  "progreso": 50
}
```

Solo el docente puede cambiar el estado o cerrar. Para usar `COMPLETADA` debe
registrar un `resultado` de al menos diez caracteres. Una accion cerrada ya no
acepta nuevas actualizaciones.

## Senales y dashboard

`GET /api/docente/seguimiento/` devuelve por estudiante `nivel_atencion`,
`senales` y conteos de acciones. Los criterios actuales son transparentes:

- asistencia menor a 85%: observar; menor a 70%: prioritario;
- alguna evidencia en C: observar; 50% o mas en C: prioritario;
- una incidencia abierta: observar; dos o mas: prioritario.

`GET /api/dashboard/` agrega a todos los roles, dentro de su alcance:
`acciones_seguimiento_pendientes`, `acciones_seguimiento_vencidas`,
`acciones_seguimiento_completadas` y el grafico `estado_acciones_seguimiento`.
