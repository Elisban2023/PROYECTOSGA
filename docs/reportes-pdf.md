# Exportacion de reportes PDF

## Endpoint

`GET /api/reportes/exportar-pdf/`

Requiere JWT y genera el documento consultando nuevamente la base de datos. El
frontend no envia filas ni contenido del informe, por lo que no puede ampliar el
alcance autorizado por el backend.

## Tipos por rol

| Rol | Valores permitidos para `tipo` |
| --- | --- |
| Administrador o directivo | `dashboard`, `resumen`, `academico`, `matriculas`, `incidencias`, `notificaciones` |
| Docente | `dashboard`, `resumen`, `asistencias`, `calificaciones`, `seguimiento` |
| Estudiante | `dashboard`, `resumen`, `asistencias`, `calificaciones`, `seguimiento` |
| Apoderado | `dashboard`, `resumen`, `asistencias`, `calificaciones`, `seguimiento` |

Filtros disponibles segun el reporte: `anio_academico`, `periodo_academico`,
`grado`, `seccion`, `docente`, `asignacion_curso`, `estudiante`, `estado`,
`nivel` y `estado_envio`. Los identificadores deben ser enteros positivos. El
apoderado solo puede seleccionar estudiantes vinculados y el estudiante no puede
seleccionar otra identidad.

Ejemplos:

```text
GET /api/reportes/exportar-pdf/?tipo=seguimiento&asignacion_curso=20
GET /api/reportes/exportar-pdf/?tipo=calificaciones&periodo_academico=3
GET /api/reportes/exportar-pdf/?tipo=incidencias&estado=ABIERTA
GET /api/reportes/exportar-pdf/?tipo=seguimiento&estudiante=30
```

La respuesta tiene `Content-Type: application/pdf` y `Content-Disposition:
attachment`. También usa `Cache-Control: private, no-store` para evitar que el
navegador o proxies compartidos almacenen información académica sensible. Cada
exportacion se registra en auditoria.
