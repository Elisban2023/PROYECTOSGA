import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from sga.models import (
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Curso,
    Docente,
    EstadoAcademico,
    EstadoEnvio,
    EstadoMatricula,
    EstadoRevisionIA,
    Estudiante,
    Grado,
    IncidenciaAcademica,
    Matricula,
    Notificacion,
    ObservacionAcademica,
    Parentesco,
    Perfil,
    RecomendacionIA,
    Seccion,
    VinculoApoderado,
)
from sga.roles import ROLE_ADMIN, ROLE_APODERADO, ROLE_DOCENTE, ROLE_ESTUDIANTE


class FakeSendGridResponse:
    status = 202

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    SENDGRID_ENABLED=True,
    SENDGRID_API_KEY="sendgrid-test-key",
    SENDGRID_FROM_EMAIL="sga@example.com",
    SENDGRID_FROM_NAME="SGA CUSCO",
    SENDGRID_TIMEOUT=5,
    FRONTEND_URL="https://sga.example.com",
)
class NotificacionesUsuarioTests(TestCase):
    def setUp(self):
        grupos = {
            rol: Group.objects.create(name=rol)
            for rol in (ROLE_ADMIN, ROLE_DOCENTE, ROLE_ESTUDIANTE, ROLE_APODERADO)
        }
        self.admin = self._usuario("admin.notifica", grupos[ROLE_ADMIN], "Admin", "SGA")
        self.docente_user = self._usuario("docente.notifica", grupos[ROLE_DOCENTE], "Rosa", "Quispe")
        self.docente = Docente.objects.create(perfil=Perfil.objects.create(user=self.docente_user))
        self.estudiante_user = self._usuario("estudiante.notifica", grupos[ROLE_ESTUDIANTE], "Luis", "Mamani")
        self.estudiante = Estudiante.objects.create(
            perfil=Perfil.objects.create(user=self.estudiante_user),
            codigo_estudiante="NOT-001",
        )
        self.ajeno_user = self._usuario("estudiante.ajeno", grupos[ROLE_ESTUDIANTE], "Eva", "Flores")
        Estudiante.objects.create(
            perfil=Perfil.objects.create(user=self.ajeno_user),
            codigo_estudiante="NOT-002",
        )
        self.apoderado_user = self._usuario("apoderado.notifica", grupos[ROLE_APODERADO], "Maria", "Mamani")
        self.apoderado = Apoderado.objects.create(
            perfil=Perfil.objects.create(user=self.apoderado_user)
        )
        VinculoApoderado.objects.create(
            apoderado=self.apoderado,
            estudiante=self.estudiante,
            parentesco=Parentesco.MADRE,
            es_principal=True,
        )
        anio = AnioAcademico.objects.create(
            anio=2026,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado=EstadoAcademico.ACTIVO,
        )
        grado = Grado.objects.create(nombre="Tercero")
        seccion = Seccion.objects.create(grado=grado, nombre="D")
        curso = Curso.objects.create(nombre="Comunicacion")
        self.asignacion = AsignacionCurso.objects.create(
            curso=curso,
            docente=self.docente,
            seccion=seccion,
            anio_academico=anio,
        )
        self.matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            seccion=seccion,
            anio_academico=anio,
            fecha_matricula=date(2026, 3, 1),
            estado=EstadoMatricula.ACTIVA,
        )
        observacion = ObservacionAcademica.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            docente=self.docente,
            fecha=timezone.now(),
            categoria="ASISTENCIA",
            descripcion="Se requiere comunicar una inasistencia reiterada.",
        )
        self.incidencia = IncidenciaAcademica.objects.create(
            matricula=self.matricula,
            observacion=observacion,
            tipo="ASISTENCIA",
            descripcion="Inasistencia pendiente de seguimiento.",
            nivel="MEDIO",
            estado="ABIERTA",
            fecha_registro=timezone.now(),
        )
        self.client = APIClient()
        self.recomendacion = RecomendacionIA.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            revisado_por_docente=self.docente,
            resumen_contexto="Contexto academico anonimizado para la prueba.",
            texto_generado=json.dumps(
                {
                    "resumen": "El estudiante requiere reforzar la continuidad de sus actividades.",
                    "fortalezas": ["Participa cuando asiste a clase."],
                    "aspectos_reforzar": ["Regularidad en la asistencia."],
                    "acciones_docente": ["Dar seguimiento semanal."],
                    "acciones_estudiante": ["Completar las actividades pendientes."],
                    "comunicacion_apoderado": "Acompanar la organizacion semanal.",
                }
            ),
            estado_revision=EstadoRevisionIA.APROBADA,
            fecha_generacion=timezone.now(),
            fecha_revision=timezone.now(),
        )

    def _payload(self, destinatarios):
        return {
            "destinatarios": destinatarios,
            "tipo": "INCIDENCIA",
            "prioridad": "ALTA",
            "titulo": "Seguimiento de asistencia",
            "mensaje": "Se registro una incidencia que requiere seguimiento oportuno.",
            "incidencia_id": self.incidencia.id,
            "accion_url": "/seguimiento/incidencias",
        }

    @patch("sga.services.correos.request.urlopen", return_value=FakeSendGridResponse())
    def test_docente_notifica_a_roles_permitidos_y_envia_cada_correo(self, urlopen):
        self.client.force_authenticate(self.docente_user)

        response = self.client.post(
            "/api/docente/notificaciones/enviar/",
            self._payload([self.estudiante_user.id, self.apoderado_user.id, self.admin.id]),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["creadas"], 3)
        self.assertEqual(response.data["correos_enviados"], 3)
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(Notificacion.objects.filter(estado_envio=EstadoEnvio.ENVIADA).count(), 3)
        self.assertTrue(
            Notificacion.objects.filter(
                destinatario=self.apoderado_user,
                apoderado=self.apoderado,
                enviado_por_docente=self.docente,
            ).exists()
        )

    def test_bandeja_polling_y_lectura_estan_aislados_por_usuario(self):
        primera = Notificacion.objects.create(
            destinatario=self.estudiante_user,
            enviado_por_docente=self.docente,
            titulo="Primera notificacion",
            mensaje="Contenido academico de la primera notificacion.",
        )
        Notificacion.objects.create(
            destinatario=self.apoderado_user,
            enviado_por_docente=self.docente,
            titulo="Notificacion privada",
            mensaje="Contenido destinado solamente al apoderado.",
        )
        segunda = Notificacion.objects.create(
            destinatario=self.estudiante_user,
            enviado_por_docente=self.docente,
            titulo="Segunda notificacion",
            mensaje="Contenido academico de la segunda notificacion.",
        )
        self.client.force_authenticate(self.estudiante_user)

        bandeja = self.client.get("/api/notificaciones/mias/")
        novedades = self.client.get(f"/api/notificaciones/mias/?desde_id={primera.id}")
        lectura = self.client.post(
            f"/api/notificaciones/mias/{segunda.id}/marcar-leida/"
        )
        resumen = self.client.get("/api/notificaciones/mias/resumen/")

        self.assertEqual(bandeja.status_code, 200)
        self.assertEqual(len(bandeja.data["results"]), 2)
        self.assertEqual([item["id"] for item in novedades.data["results"]], [segunda.id])
        self.assertEqual(lectura.status_code, 200)
        self.assertTrue(lectura.data["leida"])
        self.assertEqual(resumen.data["no_leidas"], 1)

    def test_rechaza_destinatario_ajeno_y_admin_no_puede_crear(self):
        self.client.force_authenticate(self.docente_user)
        ajeno = self.client.post(
            "/api/docente/notificaciones/enviar/",
            self._payload([self.ajeno_user.id]),
            format="json",
        )
        self.client.force_authenticate(self.admin)
        admin_crea = self.client.post(
            "/api/notificaciones/",
            {"titulo": "Intento", "mensaje": "No debe poder crear."},
            format="json",
        )

        self.assertEqual(ajeno.status_code, 400)
        self.assertEqual(admin_crea.status_code, 405)
        self.assertEqual(Notificacion.objects.count(), 0)

    @override_settings(SENDGRID_ENABLED=False)
    def test_fallo_de_correo_no_elimina_notificacion_interna(self):
        self.client.force_authenticate(self.docente_user)

        response = self.client.post(
            "/api/docente/notificaciones/enviar/",
            self._payload([self.estudiante_user.id]),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["correos_fallidos"], 1)
        notificacion = Notificacion.objects.get()
        self.assertEqual(notificacion.estado_envio, EstadoEnvio.FALLIDA)
        self.assertIsNone(notificacion.fecha_lectura)

    @patch("sga.services.correos.request.urlopen", return_value=FakeSendGridResponse())
    def test_publica_recomendacion_a_estudiante_y_apoderado_sin_duplicar(self, urlopen):
        self.client.force_authenticate(self.docente_user)
        ruta = f"/api/docente/recomendaciones-ia/{self.recomendacion.id}/publicar/"
        payload = {
            "notificar_estudiante": True,
            "notificar_apoderados": True,
            "prioridad": "ALTA",
        }

        primera = self.client.post(ruta, payload, format="json")
        segunda = self.client.post(ruta, payload, format="json")

        self.assertEqual(primera.status_code, 201)
        self.assertEqual(primera.data["creadas"], 2)
        self.assertEqual(primera.data["correos_enviados"], 2)
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(segunda.data["creadas"], 0)
        self.assertEqual(segunda.data["ya_notificados"], 2)
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(
            set(
                Notificacion.objects.filter(recomendacion=self.recomendacion).values_list(
                    "destinatario_id", flat=True
                )
            ),
            {self.estudiante_user.id, self.apoderado_user.id},
        )

    def test_no_publica_recomendacion_pendiente(self):
        self.recomendacion.estado_revision = EstadoRevisionIA.PENDIENTE
        self.recomendacion.save(update_fields=["estado_revision"])
        self.client.force_authenticate(self.docente_user)

        response = self.client.post(
            f"/api/docente/recomendaciones-ia/{self.recomendacion.id}/publicar/",
            {"notificar_estudiante": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Notificacion.objects.count(), 0)

    @staticmethod
    def _usuario(username, grupo, first_name, last_name):
        user = User.objects.create_user(
            username=username,
            password="PruebaNotificacion2026!",
            first_name=first_name,
            last_name=last_name,
            email=f"{username}@example.com",
        )
        user.groups.add(grupo)
        return user
