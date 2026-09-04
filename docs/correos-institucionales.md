# Correos institucionales

El modulo permite a Administrador y Directivo previsualizar y enviar correos a
usuarios con rol Administrador, Directivo, Docente, Estudiante o Apoderado. El
backend selecciona la plantilla segun el rol real del usuario y escapa el
contenido ingresado; el frontend no debe enviar HTML.

## Configuracion

```env
SENDGRID_ENABLED=True
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=correo-verificado@dominio.com
SENDGRID_FROM_NAME=SGA Institucion Educativa CUSCO
SENDGRID_TIMEOUT=15
FRONTEND_URL=http://localhost:5173
```

`FRONTEND_URL` se usa para construir de forma segura el enlace opcional del
boton. La API acepta solo una ruta interna, por ejemplo `/docente/mis-cursos`.

## Contrato de envio

`POST /api/correos/previsualizar/` y `POST /api/correos/enviar/` reciben:

```json
{
  "usuario_id": 15,
  "rol": "Docente",
  "asunto": "Nueva asignacion academica",
  "mensaje": "Se le asigno el curso de Matematica para el periodo actual.",
  "accion_texto": "Ver mis cursos",
  "accion_ruta": "/docente/mis-cursos"
}
```

`rol` es opcional cuando el usuario tiene un unico rol. Si se envia, debe ser
uno de sus roles reales. `accion_texto` y `accion_ruta` son opcionales, pero
deben enviarse juntos.

## Endpoints

- `GET /api/correos/plantillas/`: formatos disponibles por rol.
- `POST /api/correos/previsualizar/`: devuelve `html` y `texto` sin enviar ni guardar.
- `POST /api/correos/enviar/`: envia mediante SendGrid y registra el resultado.
- `GET /api/correos/`: historial paginado.
- `GET /api/correos/{id}/`: detalle de un envio.

El historial acepta `rol`, `estado`, `usuario`, `search` y `ordering` como
parametros de consulta. No existe `DELETE`: los registros son evidencia de
auditoria. Todos los endpoints requieren JWT y rol Administrador o Directivo.

Las notificaciones de incidencias existentes conservan sus endpoints y ahora
tambien usan el formato HTML de Apoderado, con alternativa en texto plano.

## Comunicaciones del docente

El docente puede comunicar datos reales de sus cursos a los apoderados
vinculados mediante:

- `GET /api/docente/comunicaciones/`: historial propio paginado.
- `GET /api/docente/comunicaciones/{id}/`: detalle de un envio propio.
- `POST /api/docente/comunicaciones/previsualizar/`: vista previa y destinatarios.
- `POST /api/docente/comunicaciones/enviar/`: envio a los apoderados vinculados.

El cuerpo acepta `matricula_id`, `asignacion_curso_id`, `tipo`, el
`periodo_academico_id` opcional y un `mensaje_adicional` opcional. Para
`RECOMENDACION` se exige `recomendacion_id`; para `INCIDENCIA`,
`incidencia_id`. Los tipos disponibles son `CALIFICACIONES`, `RECOMENDACION`,
`INCIDENCIA`, `ASISTENCIA` y `SEGUIMIENTO`.
