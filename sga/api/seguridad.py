from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from sga.models import TipoEventoAutenticacion
from sga.roles import get_primary_role, is_admin_or_directivo
from sga.serializers.seguridad import (
    CambiarPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    MFAVerificarSerializer,
    RecuperarPasswordConfirmarSerializer,
    RecuperarPasswordSolicitudSerializer,
    RecuperarPasswordTokenSerializer,
    TokenRefreshInactividadSerializer,
)
from sga.services.correos import CorreoError
from sga.services.seguridad import (
    cambiar_password_con_token,
    emitir_tokens,
    iniciar_desafio_mfa,
    registrar_evento_autenticacion,
    revocar_sesiones,
    solicitar_recuperacion_password,
    usuario_desde_token,
    verificar_desafio_mfa,
)


class TokenRefreshSeguroView(TokenRefreshView):
    serializer_class = TokenRefreshInactividadSerializer
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "token_refresh"


class LoginView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        user = authenticate(
            request=request,
            username=username,
            password=serializer.validated_data["password"],
        )
        if user is None:
            registrar_evento_autenticacion(
                request,
                TipoEventoAutenticacion.LOGIN_FALLIDO,
                identificador=username,
                detalle="Credenciales invalidas",
            )
            return Response(
                {"detail": "Las credenciales no son validas."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if is_admin_or_directivo(user):
            try:
                desafio = iniciar_desafio_mfa(user, request)
            except CorreoError as exc:
                registrar_evento_autenticacion(
                    request,
                    TipoEventoAutenticacion.LOGIN_FALLIDO,
                    user=user,
                    detalle="No se pudo completar MFA",
                )
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return Response(
                {
                    "mfa_required": True,
                    "challenge_id": desafio.pk,
                    "expires_in": int((desafio.expira_en - desafio.creado_en).total_seconds()),
                    "detail": "Se envio un codigo de verificacion al correo registrado.",
                },
                status=status.HTTP_202_ACCEPTED,
            )

        update_last_login(None, user)
        registrar_evento_autenticacion(
            request,
            TipoEventoAutenticacion.LOGIN_EXITOSO,
            user=user,
            exitoso=True,
        )
        return Response({"mfa_required": False, "rol": get_primary_role(user), **emitir_tokens(user)})


class MFAVerificarView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "mfa"

    @extend_schema(request=MFAVerificarSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = MFAVerificarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, error = verificar_desafio_mfa(
            serializer.validated_data["challenge_id"],
            serializer.validated_data["codigo"],
            request,
        )
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        update_last_login(None, user)
        registrar_evento_autenticacion(
            request,
            TipoEventoAutenticacion.LOGIN_EXITOSO,
            user=user,
            exitoso=True,
            detalle="Acceso con MFA",
        )
        return Response({"mfa_required": False, "rol": get_primary_role(user), **emitir_tokens(user)})


class RecuperarPasswordSolicitudView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "password_reset"

    @extend_schema(request=RecuperarPasswordSolicitudSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = RecuperarPasswordSolicitudSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        solicitar_recuperacion_password(serializer.validated_data["email"], request)
        return Response(
            {
                "detail": (
                    "Si el correo corresponde a una cuenta activa, recibira un enlace de recuperacion."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


class RecuperarPasswordValidarView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "password_reset_validate"

    @extend_schema(request=RecuperarPasswordTokenSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = RecuperarPasswordTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valido = usuario_desde_token(**serializer.validated_data) is not None
        return Response(
            {
                "valid": valido,
                "detail": "El enlace es valido." if valido else "El enlace es invalido o ha expirado.",
            },
            status=status.HTTP_200_OK if valido else status.HTTP_400_BAD_REQUEST,
        )


class RecuperarPasswordConfirmarView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "password_reset_confirm"

    @extend_schema(request=RecuperarPasswordConfirmarSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = RecuperarPasswordConfirmarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        user = cambiar_password_con_token(
            datos["uid"],
            datos["token"],
            datos["nueva_password"],
            request,
        )
        if user is None:
            return Response(
                {"detail": "El enlace es invalido o ha expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "La contrasena fue actualizada. Inicie sesion nuevamente."})


class CambiarPasswordView(APIView):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "password_change"

    @extend_schema(request=CambiarPasswordSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = CambiarPasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["nueva_password"])
        request.user.save(update_fields=["password"])
        revocar_sesiones(request.user)
        registrar_evento_autenticacion(
            request,
            TipoEventoAutenticacion.PASSWORD_CAMBIADO,
            user=request.user,
            exitoso=True,
        )
        return Response({"detail": "La contrasena fue actualizada. Inicie sesion nuevamente."})


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "logout"

    @extend_schema(request=LogoutSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token.get("user_id")) != str(request.user.pk):
                raise TokenError("Token de otro usuario")
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "El refresh token no es valido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        registrar_evento_autenticacion(
            request,
            TipoEventoAutenticacion.LOGOUT,
            user=request.user,
            exitoso=True,
        )
        return Response({"detail": "Sesion cerrada correctamente."})
