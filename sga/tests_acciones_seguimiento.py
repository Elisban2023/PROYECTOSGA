from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from sga.models import (
    AccionSeguimiento,
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
    EstadoGeneral,
    EstadoMatricula,
    Estudiante,
    Grado,
    Matricula,
    Notificacion,
    Parentesco,
    Perfil,
    PeriodoAcademico,
    Seccion,
    VinculoApoderado,
)
from sga.roles import ROLE_ADMIN, ROLE_APODERADO, ROLE_DOCENTE, ROLE_ESTUDIANTE


@override_settings(ALLOWED_HOSTS=["testserver"], SENDGRID_ENABLED=False)
class AccionesSeguimientoTests(TestCase):
    def setUp(self):
        grupos = {
            rol: Group.objects.create(name=rol)
            for rol in (ROLE_ADMIN, ROLE_DOCENTE, ROLE_ESTUDIANTE, ROLE_APODERADO)
        }
        self.admin = self._usuario("admin.acciones", grupos[ROLE_ADMIN])
        self.docente_user = self._usuario("docente.acciones", grupos[ROLE_DOCENTE])
        self.docente = Docente.objects.create(perfil=Perfil.objects.create(user=self.docente_user))
        self.estudiante_user = self._usuario("estudiante.acciones", grupos[ROLE_ESTUDIANTE])
        self.estudiante = Estudiante.objects.create(
            perfil=Perfil.objects.create(user=self.estudiante_user),
            codigo_estudiante="ACC-001",
        )
        self.ajeno_user = self._usuario("estudiante.ajeno.acciones", grupos[ROLE_ESTUDIANTE])
        Estudiante.objects.create(
            perfil=Perfil.objects.create(user=self.ajeno_user),
            codigo_estudiante="ACC-002",
        )
        self.apoderado_user = self._usuario("apoderado.acciones", grupos[ROLE_APODERADO])
        self.apoderado = Apoderado.objects.create(
            perfil=Perfil.objects.create(user=self.apoderado_user)
        )
        VinculoApoderado.objects.create(
            apoderado=self.apoderado,
            estudiante=self.estudiante,
            parentesco=Parentesco.MADRE,
            es_principal=True,
        )
        self.otro_apoderado_user = self._usuario("apoderado.ajeno.acciones", grupos[ROLE_APODERADO])
        Apoderado.objects.create(
            perfil=Perfil.objects.create(user=self.otro_apoderado_user)
        )

        self.anio = AnioAcademico.objects.create(
            anio=2026,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 12, 20),
            estado=EstadoAcademico.ACTIVO,
        )
        self.periodo = PeriodoAcademico.objects.create(
            anio_academico=self.anio,
            nombre="Tercer Bimestre",
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 10, 15),
            estado=EstadoAcademico.ACTIVO,
        )
        grado = Grado.objects.create(nombre="Primero")
        seccion = Seccion.objects.create(grado=grado, nombre="A")
        curso = Curso.objects.create(nombre="Arte y Cultura")
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
            fecha_matricula=date(2026, 3, 2),
            estado=EstadoMatricula.ACTIVA,
        )
        competencia = Competencia.objects.create(curso=curso, nombre="Crea proyectos artisticos")
        capacidad = Capacidad.objects.create(competencia=competencia, nombre="Explora lenguajes")
        self.criterio = CriterioCalificacion.objects.create(
            capacidad=capacidad,
            nombre="Desarrolla una propuesta",
        )
        self.client = APIClient()

    def payload(self, notificar=False):
        return {
            "matricula_id": self.matricula.id,
            "asignacion_curso_id": self.asignacion.id,
            "periodo_academico_id": self.periodo.id,
            "tipo": "REFUERZO",
            "responsable": "COMPARTIDA",
            "prioridad": "ALTA",
            "titulo": "Reforzar presentacion del proyecto",
            "descripcion": "Completar la propuesta artistica y revisar sus avances con el docente.",
            "fecha_limite": str(timezone.localdate() + timedelta(days=7)),
            "visible_estudiante": True,
            "visible_apoderado": True,
            "notificar_destinatarios": notificar,
        }

    def crear_accion(self, notificar=False):
        self.client.force_authenticate(self.docente_user)
        return self.client.post(
            "/api/docente/acciones-seguimiento/",
            self.payload(notificar),
            format="json",
        )

    def test_docente_crea_accion_y_notifica_a_estudiante_y_apoderado(self):
        response = self.crear_accion(notificar=True)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AccionSeguimiento.objects.count(), 1)
        self.assertEqual(Notificacion.objects.count(), 2)
        self.assertEqual(response.data["correos_fallidos"], 2)

    def test_estudiante_registra_avance_solo_en_su_accion(self):
        accion_id = self.crear_accion().data["accion"]["id"]
        self.client.force_authenticate(self.estudiante_user)
        listado = self.client.get("/api/estudiante/acciones-seguimiento/")
        avance = self.client.post(
            f"/api/estudiante/acciones-seguimiento/{accion_id}/actualizaciones/",
            {"tipo": "AVANCE", "comentario": "Complete la primera parte.", "progreso": 40},
            format="json",
        )
        self.client.force_authenticate(self.ajeno_user)
        ajeno = self.client.post(
            f"/api/estudiante/acciones-seguimiento/{accion_id}/actualizaciones/",
            {"tipo": "COMENTARIO", "comentario": "Intento no autorizado."},
            format="json",
        )

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 1)
        self.assertEqual(avance.status_code, 201)
        self.assertEqual(ajeno.status_code, 404)
        self.assertEqual(AccionSeguimiento.objects.get().estado, "EN_PROGRESO")

    def test_apoderado_participa_solo_en_acciones_vinculadas(self):
        accion_id = self.crear_accion().data["accion"]["id"]
        self.client.force_authenticate(self.apoderado_user)
        listado = self.client.get(
            f"/api/apoderado/acciones-seguimiento/?estudiante={self.estudiante.id}"
        )
        comentario = self.client.post(
            f"/api/apoderado/acciones-seguimiento/{accion_id}/actualizaciones/",
            {"tipo": "EVIDENCIA", "comentario": "Se organizo un horario de practica en casa."},
            format="json",
        )
        self.client.force_authenticate(self.otro_apoderado_user)
        ajeno = self.client.get(
            f"/api/apoderado/acciones-seguimiento/?estudiante={self.estudiante.id}"
        )

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 1)
        self.assertEqual(comentario.status_code, 201)
        self.assertEqual(ajeno.status_code, 400)

    def test_solo_docente_cierra_accion_y_debe_registrar_resultado(self):
        accion_id = self.crear_accion().data["accion"]["id"]
        ruta = f"/api/docente/acciones-seguimiento/{accion_id}/"
        sin_resultado = self.client.patch(ruta, {"estado": "COMPLETADA"}, format="json")
        completada = self.client.patch(
            ruta,
            {
                "estado": "COMPLETADA",
                "resultado": "El estudiante completo la propuesta y mejoro su presentacion.",
            },
            format="json",
        )

        self.assertEqual(sin_resultado.status_code, 400)
        self.assertEqual(completada.status_code, 200)
        self.assertIsNotNone(AccionSeguimiento.objects.get().fecha_completada)

    def test_no_permite_ocultar_accion_al_responsable(self):
        payload = self.payload()
        payload["visible_estudiante"] = False
        self.client.force_authenticate(self.docente_user)

        response = self.client.post(
            "/api/docente/acciones-seguimiento/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("visible_estudiante", response.data)

    def test_estudiante_no_declara_avance_si_no_es_responsable(self):
        payload = self.payload()
        payload["responsable"] = "DOCENTE"
        self.client.force_authenticate(self.docente_user)
        accion_id = self.client.post(
            "/api/docente/acciones-seguimiento/",
            payload,
            format="json",
        ).data["accion"]["id"]
        self.client.force_authenticate(self.estudiante_user)

        response = self.client.post(
            f"/api/estudiante/acciones-seguimiento/{accion_id}/actualizaciones/",
            {"tipo": "AVANCE", "comentario": "Reporte de avance.", "progreso": 40},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_seguimiento_devuelve_senales_y_acciones(self):
        self.crear_accion()
        for dia, estado in ((1, "FALTA"), (2, "FALTA"), (3, "PRESENTE")):
            Asistencia.objects.create(
                matricula=self.matricula,
                asignacion_curso=self.asignacion,
                fecha=date(2026, 9, dia),
                estado=estado,
            )
        segundo_criterio = CriterioCalificacion.objects.create(
            capacidad=self.criterio.capacidad,
            nombre="Sustenta su propuesta",
        )
        for criterio in (self.criterio, segundo_criterio):
            Calificacion.objects.create(
                matricula=self.matricula,
                asignacion_curso=self.asignacion,
                periodo_academico=self.periodo,
                criterio_calificacion=criterio,
                valor="C",
            )
        self.client.force_authenticate(self.docente_user)

        response = self.client.get(
            f"/api/docente/seguimiento/?asignacion_curso={self.asignacion.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["nivel_atencion"], "PRIORITARIO")
        self.assertEqual(response.data[0]["acciones"]["pendientes"], 1)
        self.assertGreaterEqual(len(response.data[0]["senales"]), 2)

    def test_administracion_supervisa_pero_no_crea(self):
        self.crear_accion()
        self.client.force_authenticate(self.admin)

        listado = self.client.get("/api/administracion/acciones-seguimiento/")
        intento = self.client.post(
            "/api/administracion/acciones-seguimiento/",
            self.payload(),
            format="json",
        )

        self.assertEqual(listado.status_code, 200)
        self.assertEqual(len(listado.data), 1)
        self.assertEqual(intento.status_code, 405)

    @staticmethod
    def _usuario(username, grupo):
        usuario = User.objects.create_user(
            username=username,
            password="AccionesPrueba2026!",
            email=f"{username}@example.com",
        )
        usuario.groups.add(grupo)
        return usuario
