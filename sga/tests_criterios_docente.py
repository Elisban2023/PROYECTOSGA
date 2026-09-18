from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from sga.models import (
    AnioAcademico,
    AsignacionCurso,
    Capacidad,
    Competencia,
    CriterioCalificacion,
    Curso,
    Docente,
    EstadoAcademico,
    EstadoGeneral,
    Grado,
    Perfil,
    RegistroAuditoria,
    Seccion,
)
from sga.roles import ROLE_DOCENTE


@override_settings(ALLOWED_HOSTS=["testserver"])
class CriteriosDocenteTests(TestCase):
    def setUp(self):
        grupo = Group.objects.create(name=ROLE_DOCENTE)
        self.docente_user = User.objects.create_user(
            username="docente.criterios",
            password="PruebaCriterios2026!",
        )
        self.docente_user.groups.add(grupo)
        docente = Docente.objects.create(
            perfil=Perfil.objects.create(user=self.docente_user)
        )
        self.otro_docente_user = User.objects.create_user(
            username="otro.docente.criterios",
            password="PruebaCriterios2026!",
        )
        self.otro_docente_user.groups.add(grupo)
        Docente.objects.create(
            perfil=Perfil.objects.create(user=self.otro_docente_user)
        )
        anio = AnioAcademico.objects.create(
            anio=2026,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado=EstadoAcademico.ACTIVO,
        )
        grado = Grado.objects.create(nombre="Primero")
        seccion = Seccion.objects.create(grado=grado, nombre="A")
        self.curso = Curso.objects.create(nombre="Comunicacion")
        otro_curso = Curso.objects.create(nombre="Matematica")
        self.asignacion = AsignacionCurso.objects.create(
            curso=self.curso,
            docente=docente,
            seccion=seccion,
            anio_academico=anio,
            estado=EstadoGeneral.ACTIVO,
        )
        competencia = Competencia.objects.create(
            curso=self.curso,
            nombre="Se comunica oralmente",
        )
        self.capacidad = Capacidad.objects.create(
            competencia=competencia,
            nombre="Adecua el texto oral",
        )
        competencia_ajena = Competencia.objects.create(
            curso=otro_curso,
            nombre="Resuelve problemas de cantidad",
        )
        self.capacidad_ajena = Capacidad.objects.create(
            competencia=competencia_ajena,
            nombre="Usa estrategias de calculo",
        )
        self.client = APIClient()

    def test_lista_capacidades_y_crea_criterio_asociado(self):
        self.client.force_authenticate(self.docente_user)
        capacidades = self.client.get(
            f"/api/docente/mis-cursos/{self.asignacion.id}/capacidades/"
        )
        creacion = self.client.post(
            f"/api/docente/mis-cursos/{self.asignacion.id}/criterios/",
            {
                "capacidad": self.capacidad.id,
                "nombre": "  Organiza   sus ideas  ",
                "descripcion": "Evalua la coherencia y secuencia de las ideas expresadas.",
            },
            format="json",
        )

        self.assertEqual(capacidades.status_code, 200)
        self.assertEqual([item["id"] for item in capacidades.data], [self.capacidad.id])
        self.assertEqual(creacion.status_code, 201)
        self.assertEqual(creacion.data["capacidad"], self.capacidad.id)
        self.assertEqual(creacion.data["nombre"], "Organiza sus ideas")
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="CREAR_CRITERIO_CALIFICACION",
                entidad_id=str(creacion.data["id"]),
            ).exists()
        )

    def test_rechaza_capacidad_de_otro_curso_y_capacidad_omitida(self):
        self.client.force_authenticate(self.docente_user)
        url = f"/api/docente/mis-cursos/{self.asignacion.id}/criterios/"
        ajena = self.client.post(
            url,
            {
                "capacidad": self.capacidad_ajena.id,
                "nombre": "Criterio no permitido",
                "descripcion": "No pertenece al curso asignado al docente autenticado.",
            },
            format="json",
        )
        omitida = self.client.post(
            url,
            {
                "nombre": "Criterio sin capacidad",
                "descripcion": "Debe ser rechazado porque no selecciona una capacidad.",
            },
            format="json",
        )

        self.assertEqual(ajena.status_code, 400)
        self.assertIn("capacidad", ajena.data)
        self.assertEqual(omitida.status_code, 400)
        self.assertIn("capacidad", omitida.data)
        self.assertEqual(CriterioCalificacion.objects.count(), 0)

    def test_otro_docente_no_crea_en_asignacion_ajena(self):
        self.client.force_authenticate(self.otro_docente_user)
        response = self.client.post(
            f"/api/docente/mis-cursos/{self.asignacion.id}/criterios/",
            {
                "capacidad": self.capacidad.id,
                "nombre": "Intento no autorizado",
                "descripcion": "Este docente no tiene asignado el curso seleccionado.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
