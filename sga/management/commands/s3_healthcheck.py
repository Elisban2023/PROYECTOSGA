import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sga.services.aws_signed_urls import AwsSignedURLService


class Command(BaseCommand):
    help = "Verifica carga, descarga e integridad en S3 sin mostrar credenciales."

    def handle(self, *args, **options):
        servicio = AwsSignedURLService()
        clave = f"{settings.AWS_S3_PREFIX}/healthchecks/sga-{uuid.uuid4().hex}.txt"
        contenido = b"SGA S3 healthcheck"
        cargado = False
        try:
            servicio.subir_bytes(
                clave,
                contenido,
                content_type="application/octet-stream",
            )
            cargado = True
            recuperado = servicio.descargar_bytes(clave, limite=1024)
            if recuperado != contenido:
                raise CommandError("S3 devolvio un contenido diferente al enviado.")
        except Exception as exc:
            if isinstance(exc, CommandError):
                raise
            raise CommandError("La verificacion de S3 no pudo completarse.") from exc
        finally:
            if cargado:
                try:
                    servicio.eliminar_objeto(clave)
                except Exception as exc:
                    raise CommandError(
                        "La carga y descarga funcionaron, pero no se pudo limpiar el archivo temporal."
                    ) from exc
        self.stdout.write(self.style.SUCCESS("S3 operativo: carga, descarga y eliminacion verificadas."))
