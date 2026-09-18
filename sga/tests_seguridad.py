import json
import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from sga.models import DesafioMFA, EventoAutenticacion, TipoEventoAutenticacion
from sga.roles import ROLE_ADMIN, ROLE_ESTUDIANTE


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
    PASSWORD_RESET_FRONTEND_PATH="/recuperar-contrasena/confirmar",
    PASSWORD_RESET_TIMEOUT=1800,
    PASSWORD_RESET_RESEND_SECONDS=60,
    MFA_CODE_TTL_MINUTES=10,
    MFA_MAX_ATTEMPTS=5,
    SESSION_IDLE_TIMEOUT_MINUTES=30,
)
class SeguridadAutenticacionTests(TestCase):
    def setUp(self):
        cache.clear()
        admin_group = Group.objects.create(name=ROLE_ADMIN)
        estudiante_group = Group.objects.create(name=ROLE_ESTUDIANTE)
        self.admin = User.objects.create_user(
            username="admin.seguro",
            password="ClaveAdministrativa2026!",
            email="admin@example.com",
            is_staff=True,
        )
        self.admin.groups.add(admin_group)
        self.estudiante = User.objects.create_user(
            username="estudiante.seguro",
            password="ClaveEstudiante2026!",
            email="estudiante@example.com",
        )
        self.estudiante.groups.add(estudiante_group)
        self.client = APIClient()

    def _post(self, url, data, **extra):
        return self.client.post(url, data, format="json", REMOTE_ADDR="127.0.0.50", **extra)

    def test_usuario_no_administrativo_recibe_jwt_directamente(self):
        respuesta = self._post(
            reverse("token_obtain_pair"),
            {"username": self.estudiante.username, "password": "ClaveEstudiante2026!"},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["mfa_required"])
        self.assertIn("access", respuesta.data)
        self.assertIn("refresh", respuesta.data)
        self.assertEqual(respuesta.data["session"]["idle_timeout_seconds"], 1800)
        self.assertTrue(
            EventoAutenticacion.objects.filter(
                user=self.estudiante,
                tipo=TipoEventoAutenticacion.LOGIN_EXITOSO,
            ).exists()
        )

    @patch("sga.services.correos.request.urlopen", return_value=FakeSendGridResponse())
    def test_administrador_completa_mfa_antes_de_recibir_jwt(self, urlopen_mock):
        login = self._post(
            reverse("token_obtain_pair"),
            {"username": self.admin.username, "password": "ClaveAdministrativa2026!"},
        )

        self.assertEqual(login.status_code, 202)
        self.assertTrue(login.data["mfa_required"])
        self.assertNotIn("access", login.data)
        payload = json.loads(urlopen_mock.call_args.args[0].data.decode("utf-8"))
        texto = payload["content"][0]["value"]
        codigo = re.search(r"\b\d{6}\b", texto).group(0)

        verificacion = self._post(
            reverse("mfa_verify"),
            {"challenge_id": login.data["challenge_id"], "codigo": codigo},
        )

        self.assertEqual(verificacion.status_code, 200)
        self.assertIn("access", verificacion.data)
        self.assertTrue(DesafioMFA.objects.get().usado)

        reutilizacion = self._post(
            reverse("mfa_verify"),
            {"challenge_id": login.data["challenge_id"], "codigo": codigo},
        )
        self.assertEqual(reutilizacion.status_code, 400)

    def test_login_fallido_no_guarda_la_contrasena(self):
        respuesta = self._post(
            reverse("token_obtain_pair"),
            {"username": self.estudiante.username, "password": "incorrecta"},
        )

        self.assertEqual(respuesta.status_code, 401)
        evento = EventoAutenticacion.objects.get(tipo=TipoEventoAutenticacion.LOGIN_FALLIDO)
        self.assertIsNone(evento.user)
        self.assertEqual(len(evento.identificador_hash), 64)
        self.assertNotIn("incorrecta", evento.detalle)

    @patch("sga.services.correos.request.urlopen", return_value=FakeSendGridResponse())
    def test_recuperacion_valida_cambia_password_y_no_permite_reutilizar(self, urlopen_mock):
        solicitud = self._post(
            reverse("password_reset_request"),
            {"email": self.estudiante.email},
        )
        self.assertEqual(solicitud.status_code, 202)
        self.assertNotIn(self.estudiante.username, solicitud.data["detail"])

        payload = json.loads(urlopen_mock.call_args.args[0].data.decode("utf-8"))
        texto = payload["content"][0]["value"]
        coincidencia = re.search(r"uid=([^&\s]+)&token=([^\s]+)", texto)
        uid, token = coincidencia.groups()

        validacion = self._post(
            reverse("password_reset_validate"),
            {"uid": uid, "token": token},
        )
        self.assertEqual(validacion.status_code, 200)
        self.assertTrue(validacion.data["valid"])

        confirmacion = self._post(
            reverse("password_reset_confirm"),
            {
                "uid": uid,
                "token": token,
                "nueva_password": "NuevaClaveSegura2026!",
                "confirmar_password": "NuevaClaveSegura2026!",
            },
        )
        self.assertEqual(confirmacion.status_code, 200)
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.check_password("NuevaClaveSegura2026!"))

        reutilizacion = self._post(
            reverse("password_reset_validate"),
            {"uid": uid, "token": token},
        )
        self.assertEqual(reutilizacion.status_code, 400)

    @patch("sga.services.correos.request.urlopen", return_value=FakeSendGridResponse())
    def test_solicitud_para_correo_inexistente_da_respuesta_generica(self, urlopen_mock):
        respuesta = self._post(
            reverse("password_reset_request"),
            {"email": "noexiste@example.com"},
        )

        self.assertEqual(respuesta.status_code, 202)
        urlopen_mock.assert_not_called()

    def test_logout_invalida_refresh_token(self):
        login = self._post(
            reverse("token_obtain_pair"),
            {"username": self.estudiante.username, "password": "ClaveEstudiante2026!"},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        respuesta = self._post(reverse("logout"), {"refresh": login.data["refresh"]})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_refresh_mantiene_sesion_activa_y_rechaza_inactividad(self):
        activo = RefreshToken.for_user(self.estudiante)
        respuesta_activa = self._post(
            reverse("token_refresh"),
            {"refresh": str(activo)},
        )
        self.assertEqual(respuesta_activa.status_code, 200)
        self.assertIn("refresh", respuesta_activa.data)
        self.assertEqual(
            respuesta_activa.data["session"]["idle_timeout_seconds"],
            1800,
        )

        inactivo = RefreshToken.for_user(self.estudiante)
        inactivo.set_iat(at_time=timezone.now() - timedelta(minutes=31))
        respuesta_inactiva = self._post(
            reverse("token_refresh"),
            {"refresh": str(inactivo)},
        )
        self.assertEqual(respuesta_inactiva.status_code, 401)
        self.assertIn("inactividad", respuesta_inactiva.data["detail"].lower())
