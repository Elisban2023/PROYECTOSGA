from rest_framework import serializers

from sga.models import (
    EstadoEnvio,
    Notificacion,
    PrioridadNotificacion,
    TipoNotificacion,
    VinculoApoderado,
)
from sga.roles import get_primary_role


class NotificacionSerializer(serializers.ModelSerializer):
    incidencia_label = serializers.StringRelatedField(source="incidencia", read_only=True)
    apoderado_label = serializers.StringRelatedField(source="apoderado", read_only=True)
    estudiante_label = serializers.SerializerMethodField()
    estudiante_codigo = serializers.SerializerMethodField()
    apoderado_email = serializers.EmailField(
        source="apoderado.perfil.user.email", read_only=True
    )
    destinatario_label = serializers.SerializerMethodField()
    destinatario_rol = serializers.SerializerMethodField()
    enviado_por_label = serializers.SerializerMethodField()
    leida = serializers.SerializerMethodField()
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)
    prioridad_label = serializers.CharField(source="get_prioridad_display", read_only=True)

    class Meta:
        model = Notificacion
        fields = (
            "id",
            "incidencia",
            "incidencia_label",
            "apoderado",
            "apoderado_label",
            "apoderado_email",
            "estudiante_label",
            "estudiante_codigo",
            "destinatario",
            "destinatario_label",
            "destinatario_rol",
            "enviado_por_docente",
            "enviado_por_label",
            "recomendacion",
            "tipo",
            "tipo_label",
            "prioridad",
            "prioridad_label",
            "titulo",
            "mensaje",
            "accion_url",
            "datos",
            "estado_envio",
            "fecha_envio",
            "fecha_lectura",
            "leida",
            "creado_en",
            "detalle_error",
            "activo",
        )
        read_only_fields = (
            "destinatario",
            "enviado_por_docente",
            "recomendacion",
            "estado_envio",
            "fecha_envio",
            "fecha_lectura",
            "creado_en",
            "detalle_error",
        )

    def get_destinatario_label(self, obj) -> str | None:
        usuario = obj.destinatario
        if usuario is None and obj.apoderado_id:
            usuario = obj.apoderado.perfil.user
        if usuario is None:
            return None
        return usuario.get_full_name().strip() or usuario.username

    def get_estudiante_label(self, obj) -> str | None:
        matricula = self._matricula_origen(obj)
        return str(matricula.estudiante) if matricula else None

    def get_estudiante_codigo(self, obj) -> str | None:
        matricula = self._matricula_origen(obj)
        return matricula.estudiante.codigo_estudiante if matricula else None

    @staticmethod
    def _matricula_origen(obj):
        if obj.incidencia_id:
            return obj.incidencia.matricula
        if obj.recomendacion_id:
            return obj.recomendacion.matricula
        return None

    def get_destinatario_rol(self, obj) -> str | None:
        usuario = obj.destinatario
        if usuario is None and obj.apoderado_id:
            usuario = obj.apoderado.perfil.user
        return get_primary_role(usuario) if usuario else None

    def get_enviado_por_label(self, obj) -> str:
        if not obj.enviado_por_docente_id:
            return "Sistema"
        usuario = obj.enviado_por_docente.perfil.user
        return usuario.get_full_name().strip() or usuario.username

    def get_leida(self, obj) -> bool:
        return obj.fecha_lectura is not None

    def validate_titulo(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("El titulo debe tener al menos 5 caracteres.")
        return value

    def validate_mensaje(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("El mensaje debe tener al menos 10 caracteres.")
        return value

    def validate(self, attrs):
        incidencia = attrs.get("incidencia", getattr(self.instance, "incidencia", None))
        apoderado = attrs.get("apoderado", getattr(self.instance, "apoderado", None))
        if incidencia is not None and incidencia.estado == "CERRADA":
            raise serializers.ValidationError(
                {"incidencia": "No se puede notificar una incidencia cerrada."}
            )
        if apoderado is not None and not apoderado.perfil.user.is_active:
            raise serializers.ValidationError(
                {"apoderado": "El apoderado seleccionado esta inactivo."}
            )
        if incidencia is not None and apoderado is not None:
            vinculado = VinculoApoderado.objects.filter(
                apoderado=apoderado,
                estudiante=incidencia.matricula.estudiante,
            ).exists()
            if not vinculado:
                raise serializers.ValidationError(
                    {"apoderado": "El apoderado no esta vinculado al estudiante de la incidencia."}
                )
        return attrs


class NotificacionEstadoSerializer(serializers.ModelSerializer):
    leida = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = ("id", "estado_envio", "fecha_envio", "fecha_lectura", "leida")
        read_only_fields = fields

    def get_leida(self, obj) -> bool:
        return obj.fecha_lectura is not None


class DestinatarioNotificacionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    rol = serializers.CharField(read_only=True)
    tiene_email = serializers.BooleanField(read_only=True)


class EnviarNotificacionSerializer(serializers.Serializer):
    destinatarios = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=20,
    )
    tipo = serializers.ChoiceField(choices=TipoNotificacion.choices)
    prioridad = serializers.ChoiceField(
        choices=PrioridadNotificacion.choices,
        default=PrioridadNotificacion.NORMAL,
    )
    titulo = serializers.CharField(min_length=5, max_length=200, trim_whitespace=True)
    mensaje = serializers.CharField(min_length=10, max_length=2000, trim_whitespace=True)
    incidencia_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    accion_url = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_destinatarios(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("No repita destinatarios en la misma operacion.")
        return value

    def validate_accion_url(self, value):
        value = value.strip()
        if value and (not value.startswith("/") or value.startswith("//")):
            raise serializers.ValidationError("Debe ser una ruta interna que empiece con '/'.")
        return value or None
