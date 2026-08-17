from rest_framework import serializers

from sga.models import EstadoEnvio, Notificacion, VinculoApoderado


class NotificacionSerializer(serializers.ModelSerializer):
    incidencia_label = serializers.StringRelatedField(source="incidencia", read_only=True)
    apoderado_label = serializers.StringRelatedField(source="apoderado", read_only=True)
    estudiante_label = serializers.StringRelatedField(source="incidencia.matricula.estudiante", read_only=True)
    estudiante_codigo = serializers.CharField(source="incidencia.matricula.estudiante.codigo_estudiante", read_only=True)
    apoderado_email = serializers.EmailField(source="apoderado.perfil.user.email", read_only=True)

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
            "titulo",
            "mensaje",
            "estado_envio",
            "fecha_envio",
            "fecha_lectura",
            "activo",
        )
        read_only_fields = ("estado_envio", "fecha_envio", "fecha_lectura")

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
            raise serializers.ValidationError({"incidencia": "No se puede notificar una incidencia cerrada."})
        if apoderado is not None and not apoderado.perfil.user.is_active:
            raise serializers.ValidationError({"apoderado": "El apoderado seleccionado esta inactivo."})
        if incidencia is not None and apoderado is not None:
            estudiante = incidencia.matricula.estudiante
            vinculado = VinculoApoderado.objects.filter(
                apoderado=apoderado,
                estudiante=estudiante,
            ).exists()
            if not vinculado:
                raise serializers.ValidationError({"apoderado": "El apoderado no esta vinculado al estudiante de la incidencia."})
        return attrs


class NotificacionEstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ("id", "estado_envio", "fecha_envio", "fecha_lectura")
        read_only_fields = fields
