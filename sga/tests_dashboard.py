from datetime import date, datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from sga.models import (
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Asistencia,
    Calificacion,
    Capacidad,
    Competencia,
    CriterioCalificacion,
    Curso,
    Docente,
    EstadoAcademico,
    EstadoAsistencia,
    EstadoIncidencia,
    EstadoMatricula,
    Estudiante,
    Grado,
    IncidenciaAcademica,
    Matricula,
    NivelLogro,
    ObservacionAcademica,
    Parentesco,
    Perfil,
    PeriodoAcademico,
    Seccion,
    VinculoApoderado,
)
from sga.roles import ROLE_ADMIN, ROLE_APODERADO, ROLE_DOCENTE, ROLE_ESTUDIANTE


@override_settings(ALLOWED_HOSTS=["testserver"])
class DashboardSeguimientoTests(TestCase):
    def setUp(self):
        grupos = {
            nombre: Group.objects.create(name=nombre)
            for nombre in (ROLE_ADMIN, ROLE_DOCENTE, ROLE_ESTUDIANTE, ROLE_APODERADO)
        }
        self.admin = self._usuario("admin.dashboard", grupos[ROLE_ADMIN])
        self.docente_user = self._usuario("docente.dashboard", grupos[ROLE_DOCENTE], "Ana", "Quispe")
        self.docente = Docente.objects.create(perfil=Perfil.objects.create(user=self.docente_user))
        self.estudiante_user = self._usuario("estudiante.dashboard", grupos[ROLE_ESTUDIANTE], "Luis", "Mamani")
        self.estudiante = Estudiante.objects.create(
            perfil=Perfil.objects.create(user=self.estudiante_user), codigo_estudiante="EST-DASH-001"
        )
        self.otro_estudiante_user = self._usuario("otro.estudiante", grupos[ROLE_ESTUDIANTE], "Eva", "Flores")
        self.otro_estudiante = Estudiante.objects.create(
            perfil=Perfil.objects.create(user=self.otro_estudiante_user), codigo_estudiante="EST-DASH-002"
        )
        self.apoderado_user = self._usuario("apoderado.dashboard", grupos[ROLE_APODERADO], "Maria", "Condori")
        self.apoderado = Apoderado.objects.create(perfil=Perfil.objects.create(user=self.apoderado_user))
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
            nombre="Primer bimestre",
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 5, 15),
            estado=EstadoAcademico.CERRADO,
        )
        grado = Grado.objects.create(nombre="Segundo")
        seccion = Seccion.objects.create(grado=grado, nombre="A")
        curso = Curso.objects.create(nombre="Matematica")
        self.asignacion = AsignacionCurso.objects.create(
            curso=curso,
            docente=self.docente,
            seccion=seccion,
            anio_academico=self.anio,
        )
        self.matricula = Matricula.objects.create(
            estudiante=self.estudiante,
            seccion=seccion,
            anio_academico=self.anio,
            fecha_matricula=date(2026, 3, 1),
            estado=EstadoMatricula.ACTIVA,
        )
        self.otra_matricula = Matricula.objects.create(
            estudiante=self.otro_estudiante,
            seccion=seccion,
            anio_academico=self.anio,
            fecha_matricula=date(2026, 3, 1),
            estado=EstadoMatricula.ACTIVA,
        )
        for dia, estado in ((2, EstadoAsistencia.PRESENTE), (3, EstadoAsistencia.FALTA)):
            Asistencia.objects.create(
                matricula=self.matricula,
                asignacion_curso=self.asignacion,
                fecha=date(2026, 3, dia),
                estado=estado,
            )
        competencia = Competencia.objects.create(curso=curso, nombre="Resuelve problemas")
        capacidad = Capacidad.objects.create(competencia=competencia, nombre="Representa cantidades")
        criterio = CriterioCalificacion.objects.create(capacidad=capacidad, nombre="Sustenta su procedimiento")
        Calificacion.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            periodo_academico=self.periodo,
            criterio_calificacion=criterio,
            valor=NivelLogro.C,
        )
        observacion = ObservacionAcademica.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            docente=self.docente,
            fecha=timezone.make_aware(datetime(2026, 3, 4, 10, 0)),
            categoria="ACADEMICA",
            descripcion="Requiere reforzar el procedimiento.",
        )
        IncidenciaAcademica.objects.create(
            matricula=self.matricula,
            observacion=observacion,
            tipo="ACADEMICA",
            descripcion="Dificultad reiterada.",
            nivel="MEDIO",
            estado=EstadoIncidencia.ABIERTA,
            fecha_registro=timezone.make_aware(datetime(2026, 3, 4, 10, 30)),
        )
        self.client = APIClient()

    def test_admin_recibe_indicadores_graficos_filtros_y_prioridades(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            f"/api/dashboard/?anio_academico={self.anio.id}&periodo_academico={self.periodo.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], ROLE_ADMIN)
        self.assertEqual(response.data["summary"]["estudiantes_priorizados"], 1)
        self.assertEqual(response.data["prioridades"][0]["estudiante_id"], self.estudiante.id)
        self.assertEqual(response.data["indicadores"][0]["valor"], 50.0)
        self.assertIn("docentes", response.data["opciones_filtro"])
        self.assertIn("seguimiento_por_docente", {item["id"] for item in response.data["graficos"]})

    def test_docente_solo_recibe_su_alcance_y_no_puede_elegir_docente(self):
        self.client.force_authenticate(self.docente_user)

        response = self.client.get(f"/api/dashboard/?periodo_academico={self.periodo.id}")
        filtro_prohibido = self.client.get(f"/api/dashboard/?docente={self.docente.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], ROLE_DOCENTE)
        self.assertEqual(response.data["summary"]["estudiantes"], 2)
        self.assertEqual(len(response.data["prioridades"]), 1)
        self.assertEqual(filtro_prohibido.status_code, 400)

    def test_estudiante_solo_visualiza_su_seguimiento(self):
        self.client.force_authenticate(self.estudiante_user)

        response = self.client.get(f"/api/dashboard/?periodo_academico={self.periodo.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], ROLE_ESTUDIANTE)
        self.assertEqual(response.data["summary"]["matriculas_activas"], 1)
        self.assertEqual(response.data["filtros_aplicados"]["anio_academico"], self.anio.id)
        self.assertEqual(response.data["prioridades"][0]["estudiante_id"], self.estudiante.id)
        self.assertNotIn(self.otro_estudiante.id, [item["estudiante_id"] for item in response.data["prioridades"]])

    def test_apoderado_solo_puede_filtrar_estudiantes_vinculados(self):
        self.client.force_authenticate(self.apoderado_user)

        response = self.client.get(f"/api/dashboard/?estudiante={self.estudiante.id}")
        ajeno = self.client.get(f"/api/dashboard/?estudiante={self.otro_estudiante.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], ROLE_APODERADO)
        self.assertEqual(response.data["summary"]["estudiantes"], 1)
        self.assertEqual(ajeno.status_code, 400)

    def test_docente_exporta_reporte_pdf_segun_su_alcance(self):
        self.client.force_authenticate(self.docente_user)

        response = self.client.get(
            f"/api/reportes/exportar-pdf/?tipo=seguimiento&asignacion_curso={self.asignacion.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertGreater(len(response.content), 1000)

    def test_estudiante_no_exporta_reporte_administrativo(self):
        self.client.force_authenticate(self.estudiante_user)

        response = self.client.get(
            "/api/reportes/exportar-pdf/?tipo=matriculas"
        )

        self.assertEqual(response.status_code, 400)

    def test_apoderado_exporta_calificaciones_de_estudiante_vinculado(self):
        self.client.force_authenticate(self.apoderado_user)

        response = self.client.get(
            f"/api/reportes/exportar-pdf/?tipo=calificaciones&estudiante={self.estudiante.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    @staticmethod
    def _usuario(username, grupo, first_name="", last_name=""):
        user = User.objects.create_user(
            username=username,
            password="PruebaDashboard2026!",
            first_name=first_name,
            last_name=last_name,
        )
        user.groups.add(grupo)
        return user
