import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

from sga.models import (
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Asistencia,
    Calificacion,
    Capacidad,
    Competencia,
    CorreoInstitucional,
    CriterioCalificacion,
    Curso,
    Docente,
    EstadoAcademico,
    EstadoCorreo,
    EstadoGeneral,
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
    PeriodoAcademico,
    RecomendacionIA,
    RegistroAuditoria,
    Seccion,
    TipoCorreo,
    VinculoApoderado,
)
from sga.roles import ROLE_APODERADO, ROLE_DOCENTE, ROLE_ESTUDIANTE


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
class CorreosInstitucionalesTests(TestCase):
    def setUp(self):
        grupo_docente = Group.objects.create(name=ROLE_DOCENTE)
        self.admin = User.objects.create_user(
            username="directivo.correo",
            password="Prueba2026!",
            is_staff=True,
        )
        self.docente = User.objects.create_user(
            username="docente.correo",
            password="Prueba2026!",
            first_name="Rosa",
            last_name="Quispe",
            email="rosa@example.com",
        )
        self.docente.groups.add(grupo_docente)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.datos = {
            "usuario_id": self.docente.pk,
            "rol": ROLE_DOCENTE,
            "asunto": "Nueva asignacion academica",
            "mensaje": "Se le asigno el curso de Matematica para el periodo actual.",
            "accion_texto": "Ver mis cursos",
            "accion_ruta": "/docente/mis-cursos",
        }

    def test_previsualiza_formato_docente_sin_guardar_registro(self):
        datos = {**self.datos, "mensaje": "Contenido seguro <script>alert('x')</script>"}

        respuesta = self.client.post(reverse("correo-previsualizar"), datos, format="json")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Actividad docente", respuesta.data["html"])
        self.assertIn("&lt;script&gt;", respuesta.data["html"])
        self.assertNotIn("<script>", respuesta.data["html"])
        self.assertEqual(CorreoInstitucional.objects.count(), 0)

    @patch("sga.services.correos.request.urlopen", return_value=FakeSendGridResponse())
    def test_envia_html_texto_guarda_historial_y_auditoria(self, urlopen_mock):
        respuesta = self.client.post(reverse("correo-enviar"), self.datos, format="json")

        self.assertEqual(respuesta.status_code, 201)
        correo = CorreoInstitucional.objects.get()
        self.assertEqual(correo.estado, EstadoCorreo.ENVIADO)
        self.assertEqual(correo.rol_destinatario, ROLE_DOCENTE)
        self.assertEqual(correo.accion_url, "https://sga.example.com/docente/mis-cursos")
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="ENVIAR_CORREO",
                entidad_id=str(correo.pk),
            ).exists()
        )

        solicitud = urlopen_mock.call_args.args[0]
        payload = json.loads(solicitud.data.decode("utf-8"))
        self.assertEqual([item["type"] for item in payload["content"]], ["text/plain", "text/html"])
        self.assertEqual(payload["personalizations"][0]["to"][0]["email"], self.docente.email)

    @override_settings(SENDGRID_ENABLED=False)
    def test_fallo_controlado_si_sendgrid_esta_deshabilitado(self):
        respuesta = self.client.post(reverse("correo-enviar"), self.datos, format="json")

        self.assertEqual(respuesta.status_code, 503)
        correo = CorreoInstitucional.objects.get()
        self.assertEqual(correo.estado, EstadoCorreo.FALLIDO)
        self.assertNotIn("sendgrid-test-key", respuesta.data["detail"])
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="ENVIO_CORREO_FALLIDO",
                entidad_id=str(correo.pk),
            ).exists()
        )

    def test_rechaza_rol_que_no_pertenece_al_usuario(self):
        datos = {**self.datos, "rol": "Estudiante"}

        respuesta = self.client.post(reverse("correo-previsualizar"), datos, format="json")

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("rol", respuesta.data)


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    SENDGRID_ENABLED=True,
    SENDGRID_API_KEY="sendgrid-test-key",
    SENDGRID_FROM_EMAIL="sga@example.com",
    SENDGRID_FROM_NAME="SGA CUSCO",
    SENDGRID_TIMEOUT=5,
    FRONTEND_URL="https://sga.example.com",
)
class ComunicacionesDocenteTests(TestCase):
    def setUp(self):
        grupo_docente = Group.objects.create(name=ROLE_DOCENTE)
        grupo_estudiante = Group.objects.create(name=ROLE_ESTUDIANTE)
        grupo_apoderado = Group.objects.create(name=ROLE_APODERADO)

        self.docente_user = User.objects.create_user(username="docente.comunica", password="Prueba2026!")
        self.docente_user.groups.add(grupo_docente)
        self.docente = Docente.objects.create(perfil=Perfil.objects.create(user=self.docente_user))
        self.otro_docente_user = User.objects.create_user(username="otro.docente.comunica", password="Prueba2026!")
        self.otro_docente_user.groups.add(grupo_docente)
        Docente.objects.create(perfil=Perfil.objects.create(user=self.otro_docente_user))

        estudiante_user = User.objects.create_user(
            username="estudiante.comunica",
            first_name="Jose",
            last_name="Mamani",
        )
        estudiante_user.groups.add(grupo_estudiante)
        self.estudiante = Estudiante.objects.create(
            perfil=Perfil.objects.create(user=estudiante_user),
            codigo_estudiante="COM-001",
        )
        apoderado_user = User.objects.create_user(
            username="apoderado.comunica",
            first_name="Maria",
            last_name="Mamani",
            email="maria@example.com",
        )
        apoderado_user.groups.add(grupo_apoderado)
        self.apoderado = Apoderado.objects.create(perfil=Perfil.objects.create(user=apoderado_user))
        VinculoApoderado.objects.create(
            apoderado=self.apoderado,
            estudiante=self.estudiante,
            parentesco=Parentesco.MADRE,
            es_principal=True,
        )

        self.anio = AnioAcademico.objects.create(
            anio=2026,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado=EstadoAcademico.ACTIVO,
        )
        self.periodo = PeriodoAcademico.objects.create(
            anio_academico=self.anio,
            nombre="Primer Bimestre",
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 5, 15),
            estado=EstadoAcademico.ACTIVO,
        )
        grado = Grado.objects.create(nombre="Segundo")
        seccion = Seccion.objects.create(grado=grado, nombre="A")
        curso = Curso.objects.create(nombre="Matematica")
        self.asignacion = AsignacionCurso.objects.create(
            curso=curso,
            docente=self.docente,
            seccion=seccion,
            anio_academico=self.anio,
            estado=EstadoGeneral.ACTIVO,
        )
        self.matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            seccion=seccion,
            anio_academico=self.anio,
            fecha_matricula=date(2026, 3, 1),
            estado=EstadoMatricula.ACTIVA,
        )
        competencia = Competencia.objects.create(curso=curso, nombre="Resuelve problemas de cantidad")
        capacidad = Capacidad.objects.create(competencia=competencia, nombre="Usa estrategias de calculo")
        criterio = CriterioCalificacion.objects.create(capacidad=capacidad, nombre="Resuelve operaciones")
        Calificacion.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            periodo_academico=self.periodo,
            criterio_calificacion=criterio,
            valor="A",
        )
        Asistencia.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            fecha=date(2026, 4, 10),
            estado="PRESENTE",
        )
        observacion = ObservacionAcademica.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            docente=self.docente,
            fecha=timezone.now(),
            categoria="Academica",
            descripcion="Necesita reforzar la resolucion ordenada de operaciones.",
        )
        self.incidencia = IncidenciaAcademica.objects.create(
            matricula=self.matricula,
            observacion=observacion,
            tipo="ACADEMICA",
            descripcion="No presento dos actividades programadas del curso.",
            nivel="MEDIO",
            estado="EN_SEGUIMIENTO",
            fecha_registro=timezone.now(),
        )
        self.recomendacion = RecomendacionIA.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            periodo_academico=self.periodo,
            revisado_por_docente=self.docente,
            resumen_contexto="Contexto academico registrado para la prueba.",
            texto_generado=json.dumps(
                {
                    "resumen": "El estudiante se encuentra en logro esperado.",
                    "fortalezas": ["Mantiene asistencia regular."],
                    "aspectos_reforzar": ["Organizar sus procedimientos."],
                    "acciones_docente": ["Brindar ejercicios graduados."],
                    "acciones_estudiante": ["Practicar operaciones diariamente."],
                    "comunicacion_apoderado": "Acompanhar la practica semanal.",
                }
            ),
            estado_revision=EstadoRevisionIA.APROBADA,
            fecha_generacion=timezone.now(),
            fecha_revision=timezone.now(),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.docente_user)

    def _datos(self, tipo):
        datos = {
            "matricula_id": self.matricula.pk,
            "asignacion_curso_id": self.asignacion.pk,
            "periodo_academico_id": self.periodo.pk,
            "tipo": tipo,
        }
        if tipo == TipoCorreo.RECOMENDACION:
            datos["recomendacion_id"] = self.recomendacion.pk
        if tipo == TipoCorreo.INCIDENCIA:
            datos["incidencia_id"] = self.incidencia.pk
        return datos

    def test_previsualiza_todos_los_tipos_con_datos_reales(self):
        for tipo in (
            TipoCorreo.CALIFICACIONES,
            TipoCorreo.RECOMENDACION,
            TipoCorreo.INCIDENCIA,
            TipoCorreo.ASISTENCIA,
            TipoCorreo.SEGUIMIENTO,
        ):
            with self.subTest(tipo=tipo):
                respuesta = self.client.post(
                    reverse("api-docente-previsualizar-comunicacion"),
                    self._datos(tipo),
                    format="json",
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.data["tipo"], tipo)
                self.assertEqual(respuesta.data["destinatarios"][0]["email"], "maria@example.com")
        self.assertEqual(CorreoInstitucional.objects.count(), 0)

    @patch("sga.services.correos.request.urlopen", return_value=FakeSendGridResponse())
    def test_envia_recomendacion_y_conserva_relaciones_y_auditoria(self, urlopen_mock):
        respuesta = self.client.post(
            reverse("api-docente-enviar-comunicacion"),
            self._datos(TipoCorreo.RECOMENDACION),
            format="json",
        )

        self.assertEqual(respuesta.status_code, 201)
        correo = CorreoInstitucional.objects.get()
        self.assertEqual(correo.destinatario, self.apoderado.perfil.user)
        self.assertEqual(correo.matricula, self.matricula)
        self.assertEqual(correo.asignacion_curso, self.asignacion)
        self.assertEqual(correo.recomendacion, self.recomendacion)
        self.assertEqual(correo.estado, EstadoCorreo.ENVIADO)
        self.assertEqual(Notificacion.objects.count(), 1)
        notificacion = Notificacion.objects.get()
        self.assertEqual(notificacion.destinatario, self.apoderado.perfil.user)
        self.assertEqual(notificacion.recomendacion, self.recomendacion)
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="ENVIAR_COMUNICACION_RECOMENDACION",
                entidad_id=str(correo.pk),
            ).exists()
        )
        self.assertTrue(urlopen_mock.called)

    def test_otro_docente_no_puede_comunicar_datos_del_curso(self):
        self.client.force_authenticate(self.otro_docente_user)

        respuesta = self.client.post(
            reverse("api-docente-previsualizar-comunicacion"),
            self._datos(TipoCorreo.INCIDENCIA),
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("asignacion_curso_id", respuesta.data)
