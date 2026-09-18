import base64
import gzip
import hashlib
import json
from datetime import date
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from sga.models import (
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Asistencia,
    BackupBaseDatos,
    Curso,
    Docente,
    EstadoAcademico,
    EstadoAsistencia,
    EstadoGeneral,
    EstadoMatricula,
    Estudiante,
    Grado,
    JustificacionInasistencia,
    Matricula,
    Notificacion,
    Perfil,
    Seccion,
    VinculoApoderado,
)
from sga.roles import ROLE_ADMIN, ROLE_APODERADO, ROLE_DOCENTE, ROLE_ESTUDIANTE
from sga.services.backups import crear_backup, restaurar_backup


AJUSTES_S3_PRUEBA = {
    "ALLOWED_HOSTS": ["testserver"],
    "SENDGRID_ENABLED": False,
    "AWS_S3_ENABLED": True,
    "API_SIGNED_URL": "https://api-s3.example.test",
    "API_SIGNED_URL_ACCESSKEY": "test-access",
    "API_SIGNED_URL_SECRETKEY": "test-secret",
    "API_SIGNED_URL_ZONE": "us-east-1",
    "AWS_S3_PREFIX": "files/adjuntos3/sga",
    "AWS_S3_MAX_JUSTIFICACION_BYTES": 8 * 1024 * 1024,
    "AWS_S3_MAX_BACKUP_BYTES": 100 * 1024 * 1024,
    "AWS_S3_MAX_BACKUP_UNCOMPRESSED_BYTES": 500 * 1024 * 1024,
    "BACKUP_ENCRYPTION_KEY": "clave-exclusiva-de-pruebas",
}


@override_settings(**AJUSTES_S3_PRUEBA)
class JustificacionesCloudTests(TestCase):
    def setUp(self):
        grupos = {
            rol: Group.objects.create(name=rol)
            for rol in (ROLE_ADMIN, ROLE_APODERADO, ROLE_DOCENTE, ROLE_ESTUDIANTE)
        }
        self.docente_user = self._usuario("docente.s3", grupos[ROLE_DOCENTE])
        self.docente = Docente.objects.create(perfil=Perfil.objects.create(user=self.docente_user))
        self.estudiante_user = self._usuario("estudiante.s3", grupos[ROLE_ESTUDIANTE])
        self.estudiante = Estudiante.objects.create(
            perfil=Perfil.objects.create(user=self.estudiante_user),
            codigo_estudiante="S3-001",
        )
        self.apoderado_user = self._usuario("apoderado.s3", grupos[ROLE_APODERADO])
        self.apoderado = Apoderado.objects.create(
            perfil=Perfil.objects.create(user=self.apoderado_user)
        )
        VinculoApoderado.objects.create(
            apoderado=self.apoderado,
            estudiante=self.estudiante,
            parentesco="MADRE",
            es_principal=True,
        )
        self.otro_apoderado_user = self._usuario("otro.apoderado.s3", grupos[ROLE_APODERADO])
        Apoderado.objects.create(perfil=Perfil.objects.create(user=self.otro_apoderado_user))
        self.admin_user = self._usuario("admin.s3", grupos[ROLE_ADMIN])

        anio = AnioAcademico.objects.create(
            anio=2026,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado=EstadoAcademico.ACTIVO,
        )
        grado = Grado.objects.create(nombre="Primero")
        seccion = Seccion.objects.create(grado=grado, nombre="A")
        curso = Curso.objects.create(nombre="Comunicacion")
        self.asignacion = AsignacionCurso.objects.create(
            curso=curso,
            docente=self.docente,
            seccion=seccion,
            anio_academico=anio,
            estado=EstadoGeneral.ACTIVO,
        )
        self.matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            seccion=seccion,
            anio_academico=anio,
            fecha_matricula=date(2026, 3, 2),
            estado=EstadoMatricula.ACTIVA,
        )
        self.asistencia = Asistencia.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            fecha=date(2026, 4, 10),
            estado=EstadoAsistencia.FALTA,
        )
        self.pdf = b"%PDF-1.4\ncontenido de prueba\n%%EOF"
        self.client = APIClient()

    @staticmethod
    def _usuario(username, grupo):
        user = User.objects.create_user(username=username, password="PruebaS3-2026!", email="test@example.com")
        user.groups.add(grupo)
        return user

    def test_flujo_apoderado_docente_valida_archivo_y_justifica_asistencia(self):
        cloud = MagicMock()
        cloud.obtener_url_carga.return_value = "https://s3.example.test/upload"
        cloud.descargar_bytes.return_value = self.pdf
        self.client.force_authenticate(self.apoderado_user)

        with patch("sga.services.justificaciones.AwsSignedURLService", return_value=cloud):
            solicitud = self.client.post(
                "/api/apoderado/justificaciones/solicitar-carga/",
                {
                    "asistencia_id": self.asistencia.id,
                    "nombre_archivo": "constancia.pdf",
                    "mime_type": "application/pdf",
                    "tamano": len(self.pdf),
                    "motivo": "Consulta medica acreditada por el establecimiento de salud.",
                },
                format="json",
            )
            self.assertEqual(solicitud.status_code, 201)
            justificacion_id = solicitud.data["justificacion"]["id"]
            confirmacion = self.client.post(
                f"/api/apoderado/justificaciones/{justificacion_id}/confirmar/",
                {"confirmar": True},
                format="json",
            )

        self.assertEqual(confirmacion.status_code, 200)
        justificacion = JustificacionInasistencia.objects.get(pk=justificacion_id)
        self.assertEqual(justificacion.estado, "PENDIENTE_REVISION")
        self.assertEqual(justificacion.archivo.sha256, hashlib.sha256(self.pdf).hexdigest())

        self.client.force_authenticate(self.docente_user)
        listado = self.client.get(
            "/api/docente/justificaciones/",
            {"asignacion_curso": self.asignacion.id},
        )
        revision = self.client.patch(
            f"/api/docente/justificaciones/{justificacion_id}/revisar/",
            {
                "estado": "APROBADA",
                "comentario": "El documento acredita correctamente la inasistencia registrada.",
            },
            format="json",
        )

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(listado.data["count"], 1)
        self.assertEqual(revision.status_code, 200)
        self.asistencia.refresh_from_db()
        self.assertEqual(self.asistencia.estado, EstadoAsistencia.JUSTIFICADA)

    def test_registrar_falta_notifica_estudiante_y_apoderado_sin_duplicar(self):
        self.client.force_authenticate(self.docente_user)
        datos = {
            "asignacion_curso": self.asignacion.id,
            "fecha": "2026-09-13",
            "registros": [
                {"matricula": self.matricula.id, "estado": EstadoAsistencia.FALTA}
            ],
        }
        primera = self.client.post(
            "/api/docente/asistencias/registrar/",
            datos,
            format="json",
        )
        segunda = self.client.post(
            "/api/docente/asistencias/registrar/",
            datos,
            format="json",
        )

        self.assertEqual(primera.status_code, 201)
        self.assertEqual(primera.data["notificaciones_generadas"], 2)
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(segunda.data["notificaciones_generadas"], 0)
        self.assertEqual(Notificacion.objects.count(), 2)
        self.assertSetEqual(
            set(Notificacion.objects.values_list("destinatario_id", flat=True)),
            {self.estudiante_user.id, self.apoderado_user.id},
        )
        self.assertTrue(primera.data["registros"][0]["puede_justificar"])
        self.assertIsNone(primera.data["registros"][0]["justificacion_activa"])

    def test_asistencia_apoderado_expone_estado_de_justificacion(self):
        self.client.force_authenticate(self.apoderado_user)
        response = self.client.get(
            "/api/apoderado/asistencia/",
            {"estudiante": self.estudiante.id},
        )

        self.assertEqual(response.status_code, 200)
        registro = next(item for item in response.data if item["id"] == self.asistencia.id)
        self.assertTrue(registro["puede_justificar"])
        self.assertIsNone(registro["justificacion_activa"])

    @patch("sga.services.justificaciones.AwsSignedURLService")
    def test_apoderado_ajeno_no_puede_crear_ni_descargar_sustento(self, cloud_class):
        self.client.force_authenticate(self.otro_apoderado_user)
        solicitud = self.client.post(
            "/api/apoderado/justificaciones/solicitar-carga/",
            {
                "asistencia_id": self.asistencia.id,
                "nombre_archivo": "constancia.pdf",
                "mime_type": "application/pdf",
                "tamano": len(self.pdf),
                "motivo": "Intento de acceso a un estudiante que no esta vinculado.",
            },
            format="json",
        )
        self.assertEqual(solicitud.status_code, 400)
        cloud_class.assert_not_called()

    def test_rechaza_archivo_cuya_firma_no_coincide_con_el_mime(self):
        cloud = MagicMock()
        cloud.obtener_url_carga.return_value = "https://s3.example.test/upload"
        cloud.descargar_bytes.return_value = b"contenido-ejecutable-no-permitido"
        self.client.force_authenticate(self.apoderado_user)
        with patch("sga.services.justificaciones.AwsSignedURLService", return_value=cloud):
            solicitud = self.client.post(
                "/api/apoderado/justificaciones/solicitar-carga/",
                {
                    "asistencia_id": self.asistencia.id,
                    "nombre_archivo": "falso.pdf",
                    "mime_type": "application/pdf",
                    "tamano": len(b"contenido-ejecutable-no-permitido"),
                    "motivo": "Documento deliberadamente invalido para verificar la proteccion.",
                },
                format="json",
            )
            respuesta = self.client.post(
                f"/api/apoderado/justificaciones/{solicitud.data['justificacion']['id']}/confirmar/",
                {"confirmar": True},
                format="json",
            )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("archivo", respuesta.data)

    def test_descarga_solo_para_personas_con_alcance_academico(self):
        from sga.models import ArchivoCloud

        archivo = ArchivoCloud.objects.create(
            tipo="JUSTIFICACION",
            clave_s3="files/adjuntos3/sga/justificaciones/2026/prueba.pdf",
            nombre_original="prueba.pdf",
            mime_type="application/pdf",
            extension="pdf",
            tamano=len(self.pdf),
            sha256=hashlib.sha256(self.pdf).hexdigest(),
            creado_por=self.apoderado_user,
            estado="DISPONIBLE",
        )
        justificacion = JustificacionInasistencia.objects.create(
            asistencia=self.asistencia,
            apoderado=self.apoderado,
            archivo=archivo,
            motivo="Atencion medica acreditada mediante un documento valido.",
            estado="PENDIENTE_REVISION",
        )
        cloud = MagicMock()
        cloud.obtener_url_descarga.return_value = "https://s3.example.test/download"
        with patch("sga.services.justificaciones.AwsSignedURLService", return_value=cloud):
            self.client.force_authenticate(self.otro_apoderado_user)
            denegado = self.client.get(
                f"/api/justificaciones/{justificacion.id}/descarga/"
            )
            self.client.force_authenticate(self.estudiante_user)
            permitido = self.client.get(
                f"/api/justificaciones/{justificacion.id}/descarga/"
            )

        self.assertEqual(denegado.status_code, 403)
        self.assertEqual(permitido.status_code, 200)
        self.assertEqual(permitido.data["url"], "https://s3.example.test/download")


@override_settings(**AJUSTES_S3_PRUEBA)
class BackupsCloudTests(TestCase):
    def setUp(self):
        grupo_admin = Group.objects.create(name=ROLE_ADMIN)
        self.admin = User.objects.create_user(username="admin.backup", password="PruebaS3-2026!")
        self.admin.groups.add(grupo_admin)
        self.owner = User.objects.create_superuser(
            username="owner.backup",
            password="PruebaS3-2026!",
            email="owner@example.com",
        )
        self.client = APIClient()

    def test_crea_backup_comprimido_cifrado_y_auditado(self):
        cloud = MagicMock()
        with patch("sga.services.backups.AwsSignedURLService", return_value=cloud):
            backup = crear_backup(user=self.admin)
        cifrado = cloud.subir_bytes.call_args.args[1]
        self.assertNotIn(b"admin.backup", cifrado)
        clave = base64.urlsafe_b64encode(
            hashlib.sha256(AJUSTES_S3_PRUEBA["BACKUP_ENCRYPTION_KEY"].encode()).digest()
        )
        paquete = json.loads(gzip.decompress(Fernet(clave).decrypt(cifrado)).decode("utf-8"))
        self.assertEqual(paquete["formato"], "sga-django-fixture-v1")
        self.assertGreater(len(paquete["objetos"]), 0)
        self.assertEqual(backup.estado, "DISPONIBLE")

    @patch("sga.api.backups.programar_backup")
    def test_solicitud_manual_responde_sin_esperar_procesamiento(self, programar):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/administracion/backups/crear/",
            {"confirmacion": "CREAR BACKUP"},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["estado"], "PROCESANDO")
        self.assertEqual(
            response.data["estado_url"],
            f'/api/administracion/backups/{response.data["id"]}/',
        )
        self.assertEqual(response["Cache-Control"], "no-store, max-age=0")
        programar.assert_called_once_with(response.data["id"])

        detalle = self.client.get(response.data["estado_url"])
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(detalle.data["id"], response.data["id"])

    def test_solo_superusuario_obtiene_url_de_descarga(self):
        cloud = MagicMock()
        cloud.obtener_url_descarga.return_value = "https://s3.example.test/download"
        with patch("sga.services.backups.AwsSignedURLService", return_value=cloud):
            backup = crear_backup(user=self.admin)
            self.client.force_authenticate(self.admin)
            backup_id = backup.id
            denegado = self.client.get(f"/api/administracion/backups/{backup_id}/descarga/")
            self.client.force_authenticate(self.owner)
            permitido = self.client.get(f"/api/administracion/backups/{backup_id}/descarga/")

        self.assertEqual(denegado.status_code, 403)
        self.assertEqual(permitido.status_code, 200)
        self.assertEqual(permitido.data["url"], "https://s3.example.test/download")

    def test_owner_elimina_archivo_s3_y_conserva_registro_logico(self):
        cloud = MagicMock()
        with patch("sga.services.backups.AwsSignedURLService", return_value=cloud):
            primero = crear_backup(user=self.owner)
            segundo = crear_backup(user=self.owner)
            self.client.force_authenticate(self.owner)
            response = self.client.delete(
                f"/api/administracion/backups/{primero.id}/",
                {"confirmacion": "ELIMINAR BACKUP"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        primero.refresh_from_db()
        primero.archivo.refresh_from_db()
        self.assertEqual(primero.estado, "ELIMINADO")
        self.assertEqual(primero.archivo.estado, "ELIMINADO")
        cloud.eliminar_objeto.assert_called_once_with(primero.archivo.clave_s3)
        self.assertEqual(segundo.estado, "DISPONIBLE")

    def test_no_permite_eliminar_ultimo_respaldo_disponible(self):
        cloud = MagicMock()
        with patch("sga.services.backups.AwsSignedURLService", return_value=cloud):
            backup = crear_backup(user=self.owner)
            self.client.force_authenticate(self.owner)
            response = self.client.delete(
                f"/api/administracion/backups/{backup.id}/",
                {"confirmacion": "ELIMINAR BACKUP"},
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        cloud.eliminar_objeto.assert_not_called()

    def test_administrador_no_puede_eliminar_respaldo(self):
        cloud = MagicMock()
        with patch("sga.services.backups.AwsSignedURLService", return_value=cloud):
            primero = crear_backup(user=self.owner)
            crear_backup(user=self.owner)
            self.client.force_authenticate(self.admin)
            response = self.client.delete(
                f"/api/administracion/backups/{primero.id}/",
                {"confirmacion": "ELIMINAR BACKUP"},
                format="json",
            )

        self.assertEqual(response.status_code, 403)
        cloud.eliminar_objeto.assert_not_called()

    def test_restauracion_recupera_datos_y_crea_respaldo_preventivo(self):
        objetos = {}
        cloud = MagicMock()

        def guardar(clave_s3, contenido, content_type="application/octet-stream"):
            objetos[clave_s3] = contenido

        def descargar(clave_s3, limite=None):
            return objetos[clave_s3]

        cloud.subir_bytes.side_effect = guardar
        cloud.descargar_bytes.side_effect = descargar
        self.owner.first_name = "Nombre original"
        self.owner.save(update_fields=["first_name"])

        with patch("sga.services.backups.AwsSignedURLService", return_value=cloud):
            backup = crear_backup(user=self.owner)
            self.owner.first_name = "Nombre modificado"
            self.owner.save(update_fields=["first_name"])
            restaurado, preventivo = restaurar_backup(user=self.owner, backup=backup)

        self.owner.refresh_from_db()
        self.assertEqual(self.owner.first_name, "Nombre original")
        self.assertEqual(restaurado.estado, "RESTAURADO")
        self.assertEqual(preventivo.tipo, "PRE_RESTAURACION")
        self.assertEqual(preventivo.estado, "DISPONIBLE")
