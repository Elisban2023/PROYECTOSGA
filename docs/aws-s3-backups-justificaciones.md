# AWS S3: respaldos y justificaciones

## Arquitectura

El bucket permanece privado. Django no entrega credenciales AWS al navegador:

1. El usuario autenticado solicita una operacion al backend SGA.
2. Django valida el rol y el alcance academico.
3. Django firma la solicitud a API Gateway con SigV4 para execute-api.
4. API Gateway devuelve una URL temporal de S3.
5. El cliente usa esa URL para cargar o descargar el objeto.
6. Django conserva solo metadatos, hash SHA-256, estados y auditoria.

Las claves se guardan bajo:

- files/adjuntos3/sga/justificaciones/{anio}/...
- files/adjuntos3/sga/backups/{anio}/...

## Variables

Las credenciales solo deben existir en .env. No deben llegar al frontend ni a Git.

~~~env
AWS_S3_ENABLED=True
API_SIGNED_URL=https://...
API_SIGNED_URL_ACCESSKEY=...
API_SIGNED_URL_SECRETKEY=...
API_SIGNED_URL_SESSION_TOKEN=
API_SIGNED_URL_ZONE=us-east-1
API_SIGNED_URL_TIMEOUT=20
AWS_S3_PREFIX=files/adjuntos3/sga
AWS_S3_MAX_JUSTIFICACION_BYTES=8388608
AWS_S3_MAX_BACKUP_BYTES=104857600
AWS_S3_MAX_BACKUP_UNCOMPRESSED_BYTES=524288000
AWS_S3_UPLOAD_PENDING_TTL_MINUTES=30
BACKUP_ENCRYPTION_KEY=...
~~~

BACKUP_ENCRYPTION_KEY debe ser un secreto aleatorio estable. Si se cambia o se
pierde, los respaldos anteriores no podran descifrarse.

## Justificaciones

Formatos admitidos: PDF, JPEG y PNG. Limite predeterminado: 8 MiB.

### Flujo del apoderado

1. Identificar una asistencia en estado FALTA o TARDE.
2. Solicitar la carga:

POST /api/apoderado/justificaciones/solicitar-carga/

~~~json
{
  "asistencia_id": 10,
  "nombre_archivo": "constancia.pdf",
  "mime_type": "application/pdf",
  "tamano": 245800,
  "motivo": "Atencion medica acreditada por el establecimiento de salud."
}
~~~

3. Ejecutar el PUT directo a carga.url usando exactamente carga.headers. El
   servicio actual firma Content-Type: application/octet-stream; cambiarlo
   produce 403 SignatureDoesNotMatch.

~~~javascript
const bytes = await file.arrayBuffer();
await fetch(carga.url, {
  method: carga.metodo,
  headers: carga.headers,
  body: bytes,
});
~~~

4. Confirmar la carga:

POST /api/apoderado/justificaciones/{id}/confirmar/

~~~json
{"confirmar": true}
~~~

Al confirmar, Django descarga el objeto para comprobar tamano, firma binaria real
y SHA-256. Luego notifica al docente responsable.

### Revision docente

- GET /api/docente/justificaciones/?estado=PENDIENTE_REVISION&asignacion_curso=ID
- GET /api/docente/justificaciones/{id}/
- PATCH /api/docente/justificaciones/{id}/revisar/

~~~json
{
  "estado": "APROBADA",
  "comentario": "El documento acredita correctamente la inasistencia."
}
~~~

Una aprobacion cambia la asistencia a JUSTIFICADA. Una aprobacion o rechazo
notifica por bandeja y correo al estudiante y al apoderado.

### Consulta y descarga

- GET /api/apoderado/justificaciones/
- DELETE /api/apoderado/justificaciones/{id}/
- GET /api/estudiante/justificaciones/
- GET /api/administracion/justificaciones/
- GET /api/justificaciones/{id}/descarga/

La descarga solo devuelve una URL temporal despues de verificar que el usuario
sea el apoderado, estudiante, docente asignado o personal administrativo.

## Respaldos

El respaldo usa dumpdata de Django para los datos de auth y sga. Antes de
subirlo, el backend:

1. genera un manifiesto;
2. serializa los objetos;
3. comprime con gzip;
4. cifra con Fernet;
5. calcula SHA-256;
6. sube el resultado a S3.

Endpoints administrativos:

- GET /api/administracion/backups/
- POST /api/administracion/backups/crear/
- GET /api/administracion/backups/{id}/descarga/ (solo superusuario)
- POST /api/administracion/backups/{id}/restaurar/ (solo superusuario)

Crear:

~~~json
{"confirmacion": "CREAR BACKUP"}
~~~

Restaurar:

~~~json
{"confirmacion": "RESTAURAR BACKUP"}
~~~

La restauracion valida hash, descifrado, formato y modelos permitidos. Ademas,
crea primero un respaldo preventivo. La carga se ejecuta dentro de una
transaccion. Es una restauracion conservadora: recupera y actualiza los objetos
del respaldo, pero no borra registros nuevos creados posteriormente.

Para recuperacion exacta ante desastre se debe complementar este mecanismo con
snapshots o respaldos nativos administrados de MariaDB.

## Automatizacion en PowerShell

Prueba manual:

~~~powershell
.\venv\Scripts\python.exe manage.py backup_sga
~~~

Verificacion segura de S3:

~~~powershell
.\venv\Scripts\python.exe manage.py s3_healthcheck
~~~

Programar un respaldo diario a las 02:00 en Windows:

~~~powershell
$Project = (Get-Location).Path
$Python = (Resolve-Path ".\venv\Scripts\python.exe").Path
$Manage = (Resolve-Path ".\manage.py").Path
$Argument = '"{0}" backup_sga' -f $Manage
$Action = New-ScheduledTaskAction -Execute $Python -Argument $Argument -WorkingDirectory $Project
$Trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
Register-ScheduledTask -TaskName "SGA-Backup-Diario" -Action $Action -Trigger $Trigger -Description "Respaldo cifrado diario del SGA en S3"
~~~

La cuenta de Windows que ejecute la tarea debe tener acceso al proyecto, al
.env, a MariaDB y a Internet.

## Configuracion S3 adicional

Para cargas directas desde React, el CORS del bucket debe permitir el origen real
del frontend, el metodo PUT y el encabezado Content-Type. No se recomienda usar
AllowedOrigins: ["*"] cuando el sistema maneja datos de menores.
