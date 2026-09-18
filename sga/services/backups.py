import base64
import gzip
import hashlib
import io
import json
import os
import tempfile
import threading
import uuid

import django
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.management import call_command
from django.db import close_old_connections, connection, transaction
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from sga.models import (
    ArchivoCloud,
    BackupBaseDatos,
    EstadoArchivoCloud,
    EstadoBackup,
    TipoArchivoCloud,
    TipoBackup,
)
from sga.services.aws_signed_urls import AwsSignedURLService


FORMATO_BACKUP = "sga-django-fixture-v1"
EXCLUSIONES_BACKUP = (
    "auth.permission",
    "sga.backupbasedatos",
    "contenttypes.contenttype",
    "sessions.session",
    "admin.logentry",
    "token_blacklist.outstandingtoken",
    "token_blacklist.blacklistedtoken",
)


def get_backups():
    return BackupBaseDatos.objects.exclude(estado=EstadoBackup.ELIMINADO).select_related(
        "archivo", "iniciado_por", "restaurado_por"
    )


def crear_backup(*, user=None, tipo=TipoBackup.MANUAL):
    backup = solicitar_backup(user=user, tipo=tipo)
    return procesar_backup(backup.id)


def solicitar_backup(*, user=None, tipo=TipoBackup.MANUAL):
    return BackupBaseDatos.objects.create(tipo=tipo, iniciado_por=user)


def programar_backup(backup_id):
    hilo = threading.Thread(
        target=_procesar_backup_en_segundo_plano,
        args=(backup_id,),
        name=f"sga-backup-{backup_id}",
        daemon=True,
    )
    hilo.start()


def _procesar_backup_en_segundo_plano(backup_id):
    close_old_connections()
    try:
        procesar_backup(backup_id)
    except Exception:
        # procesar_backup ya deja el detalle seguro y el estado ERROR persistidos.
        pass
    finally:
        close_old_connections()


def procesar_backup(backup_id):
    backup = BackupBaseDatos.objects.select_related("iniciado_por").get(pk=backup_id)
    user = backup.iniciado_por
    clave_s3 = None
    carga_completada = False
    try:
        objetos = _extraer_fixture()
        manifiesto = _construir_manifiesto(backup.tipo, len(objetos))
        paquete = {"formato": FORMATO_BACKUP, "manifiesto": manifiesto, "objetos": objetos}
        contenido = json.dumps(
            paquete,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        cifrado = _fernet().encrypt(gzip.compress(contenido, compresslevel=9))
        if len(cifrado) > settings.AWS_S3_MAX_BACKUP_BYTES:
            raise ValidationError("El respaldo supera el limite configurado para S3.")

        ahora = timezone.now()
        nombre = f"sga-{ahora.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.json.gz.fernet"
        clave_s3 = f"{settings.AWS_S3_PREFIX}/backups/{ahora.year}/{nombre}"
        AwsSignedURLService().subir_bytes(
            clave_s3,
            cifrado,
            content_type="application/octet-stream",
        )
        carga_completada = True

        with transaction.atomic():
            archivo = ArchivoCloud.objects.create(
                tipo=TipoArchivoCloud.BACKUP,
                clave_s3=clave_s3,
                nombre_original=nombre,
                mime_type="application/octet-stream",
                extension="fernet",
                tamano=len(cifrado),
                sha256=hashlib.sha256(cifrado).hexdigest(),
                creado_por=user,
                estado=EstadoArchivoCloud.DISPONIBLE,
                fecha_confirmacion=timezone.now(),
            )
            backup.archivo = archivo
            backup.estado = EstadoBackup.DISPONIBLE
            backup.manifiesto = manifiesto
            backup.fecha_finalizacion = timezone.now()
            backup.detalle_error = None
            backup.save(
                update_fields=(
                    "archivo",
                    "estado",
                    "manifiesto",
                    "fecha_finalizacion",
                    "detalle_error",
                )
            )
    except Exception:
        if carga_completada and clave_s3:
            try:
                AwsSignedURLService().eliminar_objeto(clave_s3)
            except Exception:
                pass
        backup.estado = EstadoBackup.ERROR
        backup.detalle_error = "No se pudo crear o almacenar el respaldo de forma segura."
        backup.fecha_finalizacion = timezone.now()
        backup.save(update_fields=["estado", "detalle_error", "fecha_finalizacion"])
        raise
    return backup


def restaurar_backup(*, user, backup):
    if backup.estado != EstadoBackup.DISPONIBLE or not backup.archivo_id:
        raise ValidationError({"backup": "El respaldo seleccionado no esta disponible."})

    respaldo_previo = crear_backup(user=user, tipo=TipoBackup.PRE_RESTAURACION)
    backup.estado = EstadoBackup.RESTAURANDO
    backup.detalle_error = None
    backup.save(update_fields=["estado", "detalle_error"])

    ruta_temporal = None
    try:
        cifrado = AwsSignedURLService().descargar_bytes(
            backup.archivo.clave_s3,
            limite=settings.AWS_S3_MAX_BACKUP_BYTES,
        )
        if hashlib.sha256(cifrado).hexdigest() != backup.archivo.sha256:
            raise ValidationError({"backup": "El respaldo no supera la verificacion de integridad."})
        try:
            comprimido = _fernet().decrypt(cifrado)
        except InvalidToken as exc:
            raise ValidationError(
                {"backup": "El respaldo no puede descifrarse con la clave configurada."}
            ) from exc

        contenido = _descomprimir_limitado(comprimido)
        try:
            paquete = json.loads(contenido.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError({"backup": "El formato interno del respaldo no es valido."}) from exc
        _validar_paquete(paquete)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            delete=False,
        ) as temporal:
            json.dump(paquete["objetos"], temporal, ensure_ascii=False)
            ruta_temporal = temporal.name

        with transaction.atomic():
            call_command("loaddata", ruta_temporal, verbosity=0)

        backup.refresh_from_db()
        backup.estado = EstadoBackup.RESTAURADO
        backup.restaurado_por = user
        backup.fecha_restauracion = timezone.now()
        backup.detalle_error = None
        backup.save(
            update_fields=(
                "estado",
                "restaurado_por",
                "fecha_restauracion",
                "detalle_error",
            )
        )
    except Exception:
        backup.refresh_from_db()
        backup.estado = EstadoBackup.DISPONIBLE
        backup.detalle_error = "La restauracion fallo y no se aplicaron cambios completos."
        backup.save(update_fields=["estado", "detalle_error"])
        raise
    finally:
        if ruta_temporal and os.path.exists(ruta_temporal):
            os.unlink(ruta_temporal)
    return backup, respaldo_previo


def obtener_url_descarga_backup(backup):
    if backup.estado not in (EstadoBackup.DISPONIBLE, EstadoBackup.RESTAURADO):
        raise ValidationError({"backup": "El respaldo no esta disponible."})
    if not backup.archivo_id or backup.archivo.estado != EstadoArchivoCloud.DISPONIBLE:
        raise ValidationError({"backup": "El archivo del respaldo no esta disponible."})
    return AwsSignedURLService().obtener_url_descarga(backup.archivo.clave_s3)


def eliminar_backup(*, backup):
    with transaction.atomic():
        backup = (
            BackupBaseDatos.objects.select_for_update()
            .select_related("archivo")
            .get(pk=backup.pk)
        )
        if backup.estado in (EstadoBackup.PROCESANDO, EstadoBackup.RESTAURANDO):
            raise ValidationError(
                {"backup": "No se puede eliminar un respaldo que se esta procesando o restaurando."}
            )
        if backup.estado == EstadoBackup.ELIMINADO:
            raise ValidationError({"backup": "El respaldo ya fue eliminado."})

        estados_utilizables = (EstadoBackup.DISPONIBLE, EstadoBackup.RESTAURADO)
        if backup.estado in estados_utilizables:
            disponibles = (
                BackupBaseDatos.objects.select_for_update()
                .filter(estado__in=estados_utilizables, archivo__isnull=False)
                .count()
            )
            if disponibles <= 1:
                raise ValidationError({"backup": "No se puede eliminar el ultimo respaldo disponible."})

        archivo = backup.archivo
        if archivo and archivo.estado == EstadoArchivoCloud.DISPONIBLE:
            AwsSignedURLService().eliminar_objeto(archivo.clave_s3)
            archivo.estado = EstadoArchivoCloud.ELIMINADO
            archivo.fecha_eliminacion = timezone.now()
            archivo.save(update_fields=["estado", "fecha_eliminacion"])

        backup.estado = EstadoBackup.ELIMINADO
        backup.detalle_error = None
        backup.save(update_fields=["estado", "detalle_error"])
    return backup


def _extraer_fixture():
    salida = io.StringIO()
    call_command(
        "dumpdata",
        "auth",
        "sga",
        exclude=list(EXCLUSIONES_BACKUP),
        use_natural_foreign_keys=True,
        stdout=salida,
        verbosity=0,
    )
    return json.loads(salida.getvalue() or "[]")


def _construir_manifiesto(tipo, total_objetos):
    migraciones = list(
        MigrationRecorder.Migration.objects.filter(app="sga")
        .order_by("name")
        .values_list("name", flat=True)
    )
    return {
        "formato": FORMATO_BACKUP,
        "creado_en": timezone.now().isoformat(),
        "tipo": tipo,
        "django": django.get_version(),
        "motor_base_datos": connection.vendor,
        "objetos": total_objetos,
        "ultima_migracion_sga": migraciones[-1] if migraciones else None,
        "compresion": "gzip",
        "cifrado": "Fernet-AES128-CBC-HMAC-SHA256",
    }


def _fernet():
    digest = hashlib.sha256(settings.BACKUP_ENCRYPTION_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _descomprimir_limitado(comprimido):
    limite = settings.AWS_S3_MAX_BACKUP_UNCOMPRESSED_BYTES
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(comprimido), mode="rb") as archivo:
            contenido = archivo.read(limite + 1)
    except (OSError, EOFError) as exc:
        raise ValidationError({"backup": "El contenido comprimido no es valido."}) from exc
    if len(contenido) > limite:
        raise ValidationError({"backup": "El respaldo descomprimido supera el limite permitido."})
    return contenido


def _validar_paquete(paquete):
    if not isinstance(paquete, dict) or paquete.get("formato") != FORMATO_BACKUP:
        raise ValidationError({"backup": "El archivo no corresponde a un respaldo SGA compatible."})
    objetos = paquete.get("objetos")
    manifiesto = paquete.get("manifiesto")
    if not isinstance(manifiesto, dict):
        raise ValidationError({"backup": "El respaldo no contiene un manifiesto valido."})
    migracion_backup = manifiesto.get("ultima_migracion_sga")
    if migracion_backup and not MigrationRecorder.Migration.objects.filter(
        app="sga",
        name=migracion_backup,
    ).exists():
        raise ValidationError(
            {"backup": "El respaldo requiere una version mas reciente del esquema SGA."}
        )
    if not isinstance(objetos, list):
        raise ValidationError({"backup": "El respaldo no contiene una lista de objetos valida."})
    for objeto in objetos:
        modelo = objeto.get("model") if isinstance(objeto, dict) else None
        if not isinstance(modelo, str) or not modelo.startswith(("auth.", "sga.")):
            raise ValidationError({"backup": "El respaldo contiene modelos no permitidos."})
