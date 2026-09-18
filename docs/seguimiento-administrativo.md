# Seguimiento administrativo por docente

El Administrador y el Directivo supervisan el seguimiento institucional. El
docente conserva la responsabilidad de registrar evidencias y generar, editar,
aprobar o rechazar las recomendaciones pedagogicas de sus cursos.

## Navegacion recomendada

1. Mostrar un resumen paginado de docentes.
2. Al seleccionar un docente, mostrar su cabecera, contadores y asignaciones.
3. Debajo, usar pestanas para Observaciones, Incidencias y Recomendaciones IA.
4. Mantener la opcion Todos para consultar el panorama institucional.

## Endpoints de Administrador y Directivo

- `GET /api/administracion/seguimiento/docentes/`
- `GET /api/administracion/seguimiento/docentes/{docente_id}/`
- `GET /api/observaciones/?docente={docente_id}`
- `GET /api/incidencias/?docente={docente_id}`
- `GET /api/recomendaciones-ia/?docente={docente_id}`

El listado de docentes acepta `search`, `activo`, `ordering` y los parametros
de paginacion `page` y `page_size`. Los ordenamientos permitidos son `nombre`,
`incidencias_abiertas` y `recomendaciones_pendientes`, con prefijo `-` para
orden descendente.

`/api/recomendaciones-ia/` es de solo lectura para Administrador y Directivo.
Las acciones pedagogicas se realizan exclusivamente mediante los endpoints
`/api/docente/recomendaciones-ia/` del docente autenticado y asignado al curso.

Las incidencias sin una observacion asociada no tienen un docente responsable y
solo aparecen en la vista institucional Todos.
