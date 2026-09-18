from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from sga.services.seguridad import configuracion_sesion, usuario_desde_token

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TokenRefreshInactividadSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs["refresh"])
        except TokenError as exc:
            raise InvalidToken("El refresh token no es valido o ha expirado.") from exc

        emitido_en = refresh.get("iat")
        limite = settings.SESSION_IDLE_TIMEOUT_MINUTES * 60
        if (
            not isinstance(emitido_en, int)
            or int(timezone.now().timestamp()) - emitido_en > limite
        ):
            try:
                refresh.blacklist()
            except TokenError:
                pass
            raise InvalidToken("La sesion se cerro por inactividad.")

        datos = super().validate(attrs)
        datos["session"] = configuracion_sesion()
        return datos


class MFAVerificarSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    codigo = serializers.RegexField(r"^\d{6}$", write_only=True)


class RecuperarPasswordSolicitudSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class RecuperarPasswordTokenSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=150)


class RecuperarPasswordConfirmarSerializer(RecuperarPasswordTokenSerializer):
    nueva_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirmar_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["nueva_password"] != attrs["confirmar_password"]:
            raise serializers.ValidationError(
                {"confirmar_password": "Las contrasenas no coinciden."}
            )
        user = usuario_desde_token(attrs["uid"], attrs["token"])
        if user is None:
            raise serializers.ValidationError({"token": "El enlace es invalido o ha expirado."})
        try:
            validate_password(attrs["nueva_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"nueva_password": list(exc.messages)})
        return attrs


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True, trim_whitespace=False)
    nueva_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirmar_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["password_actual"]):
            raise serializers.ValidationError(
                {"password_actual": "La contrasena actual no es correcta."}
            )
        if attrs["nueva_password"] != attrs["confirmar_password"]:
            raise serializers.ValidationError(
                {"confirmar_password": "Las contrasenas no coinciden."}
            )
        try:
            validate_password(attrs["nueva_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"nueva_password": list(exc.messages)})
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)
