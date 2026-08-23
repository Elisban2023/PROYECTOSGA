import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from sga.models import (
    AnioAcademico,
    AsignacionCurso,
    Asistencia,
    Curso,
    Docente,
    EstadoAcademico,
    EstadoGeneral,
    EstadoMatricula,
    Estudiante,
    Grado,
    Matricula,
    Perfil,
    PeriodoAcademico,
    RecomendacionIA,
    RegistroAuditoria,
    Seccion,
)
from sga.roles import ROLE_DOCENTE, ROLE_ESTUDIANTE
from sga.services.recomendaciones_docente import get_recomendaciones_publicadas


class FakeOpenAIResponse:
    def __init__(self, contenido):
        self.body = json.dumps(
            {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(contenido),
                            }
                        ]
                    }
                ]
            }
        ).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


@override_settings(
    ALLOWED_HOSTS=["testserver"],
    OPENAI_ENABLED=True,
    OPENAI_API_KEY="test-key",
    OPENAI_MODEL="gpt-test",
    OPENAI_API_URL="https://api.openai.test/v1/responses",
    OPENAI_TIMEOUT=5,
    OPENAI_MAX_OUTPUT_TOKENS=500,
)
class RecomendacionesIATests(TestCase):
    def setUp(self):
        docente_group = Group.objects.create(name=ROLE_DOCENTE)
        estudiante_group = Group.objects.create(name=ROLE_ESTUDIANTE)

        self.docente_user = User.objects.create_user(
            username="docente.ia",
            password="Prueba2026!",
            first_name="Rosa",
            last_name="Quispe",
        )
        self.docente_user.groups.add(docente_group)
        docente_perfil = Perfil.objects.create(user=self.docente_user)
        self.docente = Docente.objects.create(perfil=docente_perfil)

        otro_user = User.objects.create_user(username="otro.docente")
        otro_user.groups.add(docente_group)
        otro_perfil = Perfil.objects.create(user=otro_user)
        self.otro_docente = Docente.objects.create(perfil=otro_perfil)

        self.estudiante_user = User.objects.create_user(username="estudiante.ia")
        self.estudiante_user.groups.add(estudiante_group)
        estudiante_perfil = Perfil.objects.create(user=self.estudiante_user)
        self.estudiante = Estudiante.objects.create(
            perfil=estudiante_perfil,
            codigo_estudiante="IA-2026-001",
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
        grado = Grado.objects.create(nombre="Primero")
        seccion = Seccion.objects.create(grado=grado, nombre="A")
        curso = Curso.objects.create(nombre="Comunicacion")
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
        Asistencia.objects.create(
            matricula=self.matricula,
            asignacion_curso=self.asignacion,
            fecha=date(2026, 4, 10),
            estado="PRESENTE",
        )
        self.client = APIClient()
        self.contenido_ia = {
            "resumen": "El estudiante mantiene asistencia regular en el curso.",
            "fortalezas": ["Asistencia constante."],
            "aspectos_reforzar": ["Aun no hay calificaciones suficientes."],
            "acciones_docente": ["Registrar nuevas evidencias de aprendizaje."],
            "acciones_estudiante": ["Mantener la participacion en clase."],
            "comunicacion_apoderado": "Compartir los avances cuando existan mas evidencias.",
        }

    def generar(self):
        self.client.force_authenticate(self.docente_user)
        with patch(
            "sga.services.recomendaciones_docente.request.urlopen",
            return_value=FakeOpenAIResponse(self.contenido_ia),
        ):
            return self.client.post(
                "/api/docente/recomendaciones-ia/generar/",
                {
                    "matricula": self.matricula.id,
                    "asignacion_curso": self.asignacion.id,
                    "periodo_academico": self.periodo.id,
                },
                format="json",
            )

    def test_docente_genera_recomendacion_estructurada_y_auditada(self):
        response = self.generar()

        self.assertEqual(response.status_code, 201)
        recomendacion = RecomendacionIA.objects.get()
        self.assertEqual(recomendacion.asignacion_curso, self.asignacion)
        self.assertEqual(response.data["contenido_generado"], self.contenido_ia)
        contexto = json.loads(recomendacion.resumen_contexto)
        self.assertEqual(contexto["curso"]["nombre"], "Comunicacion")
        self.assertNotIn("Rosa", recomendacion.resumen_contexto)
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="GENERAR_RECOMENDACION_IA",
                entidad_id=str(recomendacion.id),
            ).exists()
        )

    def test_otro_docente_no_puede_ver_ni_revisar_recomendacion(self):
        recomendacion_id = self.generar().data["id"]
        self.client.force_authenticate(self.otro_docente.perfil.user)

        detalle = self.client.get(
            f"/api/docente/recomendaciones-ia/{recomendacion_id}/"
        )
        revision = self.client.patch(
            f"/api/docente/recomendaciones-ia/{recomendacion_id}/revisar/",
            {"estado_revision": "APROBADA"},
            format="json",
        )

        self.assertEqual(detalle.status_code, 404)
        self.assertEqual(revision.status_code, 404)

    def test_recomendacion_solo_es_publica_despues_de_revision(self):
        recomendacion_id = self.generar().data["id"]
        self.assertEqual(get_recomendaciones_publicadas(self.matricula), [])

        self.client.force_authenticate(self.docente_user)
        revision = self.client.patch(
            f"/api/docente/recomendaciones-ia/{recomendacion_id}/revisar/",
            {
                "estado_revision": "EDITADA",
                "texto_revisado": "Recomendacion revisada y lista para compartir.",
            },
            format="json",
        )

        self.assertEqual(revision.status_code, 200)
        publicadas = get_recomendaciones_publicadas(self.matricula)
        self.assertEqual(len(publicadas), 1)
        self.assertEqual(
            publicadas[0]["texto"],
            "Recomendacion revisada y lista para compartir.",
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion="REVISAR_RECOMENDACION_EDITADA",
                entidad_id=str(recomendacion_id),
            ).exists()
        )

        self.client.force_authenticate(self.estudiante_user)
        seguimiento = self.client.get("/api/estudiante/mi-seguimiento/")
        self.assertEqual(seguimiento.status_code, 200)
        self.assertEqual(len(seguimiento.data[0]["recomendaciones"]), 1)
