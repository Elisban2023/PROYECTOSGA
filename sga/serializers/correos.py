from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers

from sga.models import CorreoInstitucional
from sga.roles import ALL_ROLES, get_primary_role, get_user_roles

User = get_user_model()


class CorreoSolicitudSerializer(serializers.Serializer):
    usuario_id = serializers.PrimaryKeyRelatedField(
        source="destinatario",
        queryset=User.objects.filter(is_active=True),
    )
    rol = serializers.ChoiceField(choices=ALL_ROLES, required=False)
    asunto = serializers.CharField(min_length=5, max_length=200, trim_whitespace=True)
    mensaje = serializers.CharField(min_length=10, trim_whitespace=True)
    accion_texto = serializers.CharField(max_length=80, required=False, allow_blank=True)
    accion_ruta = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate(self, attrs):
        destinatario = attrs["destinatario"]
        if not destinatario.email:
            raise serializers.ValidationError({"usuario_id": "El usuario no tiene correo electronico registrado."})

        roles = get_user_roles(destinatario)
        if not roles:
            raise serializers.ValidationError({"usuario_id": "El usuario no tiene un rol reconocido en el SGA."})
        rol = attrs.get("rol") or get_primary_role(destinatario)
        if rol not in roles:
            raise serializers.ValidationError({"rol": "El usuario no tiene asignado el rol indicado."})
        attrs["rol"] = rol

        accion_texto = attrs.get("accion_texto", "").strip()
        accion_ruta = attrs.get("accion_ruta", "").strip()
        if bool(accion_texto) != bool(accion_ruta):
            raise serializers.ValidationError(
                {"accion_ruta": "El texto y la ruta de accion deben enviarse juntos."}
            )
        if accion_ruta and (not accion_ruta.startswith("/") or accion_ruta.startswith("//")):
            raise serializers.ValidationError(
                {"accion_ruta": "Debe ser una ruta interna valida que comience con /."}
            )
        attrs["accion_texto"] = accion_texto or None
        attrs["accion_url"] = f"{settings.FRONTEND_URL}{accion_ruta}" if accion_ruta else None
        attrs.pop("accion_ruta", None)
        return attrs


class CorreoInstitucionalSerializer(serializers.ModelSerializer):
    destinatario_nombre = serializers.SerializerMethodField()
    destinatario_email = serializers.EmailField(source="destinatario.email", read_only=True)
    enviado_por_username = serializers.CharField(source="enviado_por.username", read_only=True)

    class Meta:
        model = CorreoInstitucional
        fields = (
            "id",
            "destinatario",
            "destinatario_nombre",
            "destinatario_email",
            "enviado_por",
            "enviado_por_username",
            "rol_destinatario",
            "tipo",
            "matricula",
            "asignacion_curso",
            "periodo_academico",
            "recomendacion",
            "incidencia",
            "asunto",
            "mensaje",
            "accion_texto",
            "accion_url",
            "estado",
            "detalle_error",
            "fecha_creacion",
            "fecha_envio",
        )
        read_only_fields = fields

    def get_destinatario_nombre(self, obj) -> str:
        return obj.destinatario.get_full_name().strip() or obj.destinatario.username
