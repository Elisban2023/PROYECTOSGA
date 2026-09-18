# Autenticacion y recuperacion de contrasena

## Login

`POST /api/auth/token/`

```json
{
  "username": "usuario",
  "password": "contrasena"
}
```

Docente, Estudiante y Apoderado reciben `access` y `refresh` con estado `200`.
Owner, Administrador y Directivo reciben estado `202`:

```json
{
  "mfa_required": true,
  "challenge_id": "uuid",
  "expires_in": 600,
  "detail": "Se envio un codigo de verificacion al correo registrado."
}
```

El frontend debe mostrar el formulario para el codigo de seis digitos y llamar:

`POST /api/auth/mfa/verify/`

```json
{
  "challenge_id": "uuid",
  "codigo": "123456"
}
```

Solo despues de verificar MFA se devuelven los JWT. El codigo caduca, se puede
usar una vez y se bloquea al superar el maximo de intentos.

## Recuperacion

1. `POST /api/auth/password-reset/request/` con `{"email": "usuario@example.com"}`.
2. La API siempre responde `202` con un mensaje generico.
3. El correo abre
   `/recuperar-contrasena/confirmar?uid=...&token=...` en el frontend.
4. La pagina envia `uid` y `token` a `POST /api/auth/password-reset/validate/`.
5. Solo si responde `200` y `valid: true`, habilita los campos de contrasena.
6. La pagina llama a `POST /api/auth/password-reset/confirm/`.

```json
{
  "uid": "identificador",
  "token": "token-firmado",
  "nueva_password": "NuevaClaveSegura2026!",
  "confirmar_password": "NuevaClaveSegura2026!"
}
```

Al confirmar, el enlace deja de funcionar y se revocan todos los refresh tokens
vigentes del usuario. La contrasena debe cumplir los validadores de Django y
tener al menos 12 caracteres.

## Sesion

La sesion usa un tiempo de inactividad configurable mediante
SESSION_IDLE_TIMEOUT_MINUTES (30 minutos por defecto). Cada respuesta de login y
refresh incluye session con idle_timeout_seconds, access_expires_in_seconds y
refresh_rotation.

El frontend debe renovar el access token solamente cuando exista actividad real
o una solicitud del usuario. No debe ejecutar refresh en segundo plano mientras
la aplicacion esta inactiva. Si la ultima renovacion supera el limite, el backend
rechaza el refresh porque la sesion se cerro por inactividad.

La rotacion permite que una sesion activa continue sin cerrarse por un tiempo
total fijo.

- `POST /api/auth/token/refresh/`: rota el refresh y bloquea el anterior.
- `POST /api/auth/logout/`: recibe `{"refresh": "..."}` y lo bloquea.
- `POST /api/auth/password/change/`: requiere JWT y recibe la contrasena actual,
  la nueva y su confirmacion.

En produccion, `DJANGO_ADMIN_ENABLED` y `API_DOCS_ENABLED` deben permanecer en
`False`, salvo que esos accesos esten protegidos adicionalmente por VPN o lista
de IP permitidas.
