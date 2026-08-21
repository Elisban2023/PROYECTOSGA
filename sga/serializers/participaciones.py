from rest_framework import serializers

from sga.models import Participacion, TipoParticipacion


class ParticipacionDatosSerializer(serializers.Serializer):
    fecha = serializers.DateTimeField()
    tipo = serializers.ChoiceField(choices=TipoParticipacion.choices)
    periodo_academico = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    valor = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=20,
    )
    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=500,
    )

    def validate_valor(self, value):
        return (value or "").strip() or None

    def validate_observacion(self, value):
        return (value or "").strip() or None


class RegistrarParticipacionSerializer(ParticipacionDatosSerializer):
    matricula = serializers.IntegerField(min_value=1)
    asignacion_curso = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if not attrs.get("valor") and not attrs.get("observacion"):
            raise serializers.ValidationError(
                "Registre un valor o una observacion para la participacion."
            )
        return attrs


class ActualizarParticipacionSerializer(ParticipacionDatosSerializer):
    fecha = serializers.DateTimeField(required=False)
    tipo = serializers.ChoiceField(choices=TipoParticipacion.choices, required=False)


class ParticipacionDocenteSerializer(serializers.ModelSerializer):
    matricula_id = serializers.IntegerField(read_only=True)
    estudiante_id = serializers.IntegerField(source="matricula.estudiante_id", read_only=True)
    estudiante_codigo = serializers.CharField(
        source="matricula.estudiante.codigo_estudiante",
        read_only=True,
    )
    estudiante_nombre = serializers.CharField(
        source="matricula.estudiante.perfil.user.get_full_name",
        read_only=True,
    )
    asignacion_curso_id = serializers.IntegerField(read_only=True)
    curso_nombre = serializers.CharField(source="asignacion_curso.curso.nombre", read_only=True)
    seccion_nombre = serializers.CharField(
        source="asignacion_curso.seccion.nombre",
        read_only=True,
    )
    periodo_academico_id = serializers.IntegerField(read_only=True)
    periodo_nombre = serializers.CharField(
        source="periodo_academico.nombre",
        read_only=True,
        allow_null=True,
    )
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Participacion
        fields = (
            "id",
            "matricula_id",
            "estudiante_id",
            "estudiante_codigo",
            "estudiante_nombre",
            "asignacion_curso_id",
            "curso_nombre",
            "seccion_nombre",
            "periodo_academico_id",
            "periodo_nombre",
            "fecha",
            "tipo",
            "tipo_label",
            "valor",
            "observacion",
        )
