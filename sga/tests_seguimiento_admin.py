from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from sga.models import (
    AnioAcademico,
    AsignacionCurso,
    Curso,
    Docente,
    EstadoAcademico,
    EstadoGeneral,
    EstadoIncidencia,
    EstadoMatricula,
    EstadoRevisionIA,
    Estudiante,
    Grado,
    IncidenciaAcademica,
    Matricula,
    ObservacionAcademica,
    Perfil,
    RecomendacionIA,
    Seccion,
)
from sga.roles import ROLE_ADMIN, ROLE_DOCENTE


@override_settings(ALLOWED_HOSTS=["testserver"])
class SeguimientoAdministrativoTests(TestCase):
    def setUp(self):
        grupo_admin = Group.objects.create(name=ROLE_ADMIN)
        grupo_docente = Group.objects.create(name=ROLE_DOCENTE)

        self.admin = User.objects.create_user(username="admin.seguimiento", password="Prueba2026!")
        self.admin.groups.add(grupo_admin)

        self.docente_user = User.objects.create_user(
            username="docente.uno",
            first_name="Rosa",
            last_name="Quispe",
        )
        self.docente_user.groups.add(grupo_docente)
        self.docente = Docente.objects.create(perfil=Perfil.objects.create(user=self.docente_user))

        otro_user = User.objects.create_user(
            username="docente.dos",
            first_name="Luis",
            last_name="Mamani",
        )
        otro_user.groups.add(grupo_docente)
        self.otro_docente = Docente.objects.create(perfil=Perfil.objects.create(user=otro_user))

        estudiante_user = User.objects.create_user(username="estudiante.seguimiento")
        estudiante = Estudiante.objects.create(
            perfil=Perfil.objects.create(user=estudiante_user),
            codigo_estudiante="SEG-001",
        )
        anio = AnioAcademico.objects.create(
            anio=2026,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado=EstadoAcademico.ACTIVO,
        )
        grado = Grado.objects.create(nombre="Tercero")
        seccion = Seccion.objects.create(grado=grado, nombre="A")
        curso = Curso.objects.create(nombre="Matematica")
        self.asignacion = AsignacionCurso.objects.create(
            curso=curso,
            docente=self.docente,
            seccion=seccion,
            anio_academico=anio,
            estado=EstadoGeneral.ACTIVO,
        )
        matricula = Matricula.objects.create(
            estudiante=estudiante,
            seccion=seccion,
            anio_academico=anio,
            fecha_matricula=date(2026, 3, 1),
            estado=EstadoMatricula.ACTIVA,
        )
        self.observacion = ObservacionAcademica.objects.create(
            matricula=matricula,
            asignacion_curso=self.asignacion,
            docente=self.docente,
            fecha=timezone.now(),
            categoria="ACADEMICA",
            descripcion="Requiere seguimiento en resolucion de problemas.",
        )
        self.incidencia = IncidenciaAcademica.objects.create(
            matricula=matricula,
            observacion=self.observacion,
            tipo="ACADEMICA",
            descripcion="Dificultad reiterada en actividades del curso.",
            nivel="MEDIO",
            estado=EstadoIncidencia.ABIERTA,
            fecha_registro=timezone.now(),
        )
        self.recomendacion = RecomendacionIA.objects.create(
            matricula=matricula,
            asignacion_curso=self.asignacion,
            resumen_contexto='{"curso": "Matematica"}',
            texto_generado='{"resumen": "Reforzar progresivamente."}',
            estado_revision=EstadoRevisionIA.PENDIENTE,
            fecha_generacion=timezone.now(),
        )
        self.client = APIClient()

    def test_lista_docentes_con_contadores_y_detalle(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/administracion/seguimiento/docentes/")
        detalle = self.client.get(
            f"/api/administracion/seguimiento/docentes/{self.docente.id}/"
        )

        self.assertEqual(response.status_code, 200)
        docente = next(item for item in response.data["results"] if item["id"] == self.docente.id)
        self.assertEqual(docente["asignaciones_activas"], 1)
        self.assertEqual(docente["observaciones_total"], 1)
        self.assertEqual(docente["incidencias_total"], 1)
        self.assertEqual(docente["incidencias_abiertas"], 1)
        self.assertEqual(docente["recomendaciones_total"], 1)
        self.assertEqual(docente["recomendaciones_pendientes"], 1)
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(len(detalle.data["asignaciones"]), 1)

    def test_filtros_de_pestanas_usan_el_docente_responsable(self):
        self.client.force_authenticate(self.admin)

        observaciones = self.client.get(f"/api/observaciones/?docente={self.docente.id}")
        incidencias = self.client.get(f"/api/incidencias/?docente={self.docente.id}")
        recomendaciones = self.client.get(
            f"/api/recomendaciones-ia/?docente={self.docente.id}"
        )
        incidencias_otro = self.client.get(
            f"/api/incidencias/?docente={self.otro_docente.id}"
        )

        self.assertEqual(observaciones.data["count"], 1)
        self.assertEqual(incidencias.data["count"], 1)
        self.assertEqual(recomendaciones.data["count"], 1)
        self.assertEqual(incidencias_otro.data["count"], 0)

    def test_recomendaciones_administrativas_son_solo_lectura(self):
        self.client.force_authenticate(self.admin)

        listado = self.client.get("/api/recomendaciones-ia/")
        creacion = self.client.post("/api/recomendaciones-ia/", {}, format="json")

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(creacion.status_code, 405)

    def test_docente_no_puede_acceder_al_resumen_administrativo(self):
        self.client.force_authenticate(self.docente_user)

        response = self.client.get("/api/administracion/seguimiento/docentes/")

        self.assertEqual(response.status_code, 403)
