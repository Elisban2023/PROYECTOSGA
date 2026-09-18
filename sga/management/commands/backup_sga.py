from django.core.management.base import BaseCommand, CommandError

from sga.models import RegistroAuditoria, TipoBackup
from sga.services.backups import crear_backup


class Command(BaseCommand):
    help = "Crea un respaldo cifrado del SGA y lo almacena mediante la API de URLs firmadas."

    def handle(self, *args, **options):
        try:
            backup = crear_backup(tipo=TipoBackup.AUTOMATICO)
        except Exception as exc:
            raise CommandError("No se pudo completar el respaldo automatico.") from exc
        RegistroAuditoria.registrar_evento(
            accion="CREAR_BACKUP_AUTOMATICO",
            modulo="configuracion",
            entidad="BackupBaseDatos",
            entidad_id=str(backup.id),
        )
        self.stdout.write(self.style.SUCCESS(f"Backup {backup.id} almacenado correctamente."))
