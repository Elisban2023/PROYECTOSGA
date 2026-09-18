# Dashboard de seguimiento academico

## Endpoint

`GET /api/dashboard/`

Requiere `Authorization: Bearer <access_token>`. La respuesta se adapta al rol autenticado y el backend limita los datos a su alcance. El frontend no debe enviar ni confiar en un rol almacenado localmente para ampliar ese alcance.

## Filtros

| Parametro | Administrador/Directivo | Docente | Estudiante | Apoderado |
|---|---:|---:|---:|---:|
| `anio_academico` | Si | Si | Si | Si |
| `periodo_academico` | Si | Si | Si | Si |
| `grado` | Si | Si | No | No |
| `seccion` | Si | Si | No | No |
| `docente` | Si | No | No | No |
| `asignacion_curso` | Si | Si | Si | No |
| `estudiante` | No | No | No | Si, solo vinculados |

Los identificadores disponibles se entregan en `opciones_filtro`. Un filtro ajeno al rol o fuera de su alcance devuelve `400`.

Ejemplo:

```http
GET /api/dashboard/?anio_academico=1&periodo_academico=3&docente=8
Authorization: Bearer eyJ...
```

## Respuesta

- `role`: rol efectivo del usuario.
- `filtros_aplicados`: filtros validados por el backend.
- `opciones_filtro`: opciones que el usuario puede seleccionar.
- `summary`: contadores anteriores, conservados por compatibilidad.
- `indicadores`: valor, unidad, interpretacion y estado (`bien`, `alerta` o `sin_datos`).
- `graficos`: series listas para donut, barras y barras apiladas.
- `prioridades`: estudiantes que requieren revision dentro del alcance del rol.
- `items`: asignaciones o matriculas usadas por las vistas anteriores.
- `meta`: fecha de calculo y criterio de priorizacion.

`summary` incluye ademas acciones de seguimiento pendientes, vencidas y
completadas. `graficos` contiene `estado_acciones_seguimiento`, lo que permite
abrir directamente el trabajo pendiente desde el dashboard.

## Indicadores educativos

- Asistencia efectiva: presentes y faltas justificadas entre el total de asistencias registradas.
- Evidencias B/C: proporcion de calificaciones `B` (en proceso) y `C` (en inicio).
- Incidencias sin resolver: incidencias abiertas o en seguimiento.
- Seguimiento prioritario: estudiante con asistencia efectiva menor al 80%, al menos una evidencia B/C o una incidencia sin resolver.

La priorizacion es orientativa. No es un diagnostico, no ordena el rendimiento general de los estudiantes y siempre requiere interpretacion humana.

## Graficos por rol

- Administrador/Directivo: asistencia, niveles de logro, incidencias por estado/nivel y actividad de seguimiento por docente.
- Docente: indicadores, estudiantes priorizados y acciones de sus asignaciones.
- Estudiante: informacion propia, participaciones, recomendaciones aprobadas y acciones visibles.
- Apoderado: informacion exclusiva de sus estudiantes vinculados y acciones visibles; puede seleccionar uno de ellos.

Cuando una serie no tiene registros, el backend devuelve sus categorias con valor `0`. El frontend debe mostrar un estado vacio en lugar de interpretar el cero como bajo rendimiento.
