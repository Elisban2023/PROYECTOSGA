from rest_framework import serializers

from sga.models import Calificacion, NivelLogro


class RegistroCalificacionItemSerializer(serializers.Serializer):
    matricula = serializers.IntegerField(min_value=1)
    valor = serializers.ChoiceField(choices=NivelLogro.choices)
    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=500,
    )

    def validate_observacion(self, value):
        return (value or "").strip() or None


class RegistrarCalificacionesSerializer(serializers.Serializer):
    asignacion_curso = serializers.IntegerField(min_value=1)
    periodo_academico = serializers.IntegerField(min_value=1)
    criterio_calificacion = serializers.IntegerField(min_value=1)
    registros = RegistroCalificacionItemSerializer(many=True, allow_empty=False)

    def validate_registros(self, value):
        matricula_ids = [registro["matricula"] for registro in value]
        if len(matricula_ids) != len(set(matricula_ids)):
            raise serializers.ValidationError(
                "No puede registrar una calificacion mas de una vez para la misma matricula."
            )
        return value


class ActualizarCalificacionSerializer(serializers.Serializer):
    valor = serializers.ChoiceField(choices=NivelLogro.choices)
    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=500,
    )

    def validate_observacion(self, value):
        return (value or "").strip() or None


class CalificacionDocenteSerializer(serializers.ModelSerializer):
    matricula_id = serializers.IntegerField(read_only=True)
    estudiante_id = serializers.IntegerField(
        source="matricula.estudiante_id",
        read_only=True,
    )
    estudiante_codigo = serializers.CharField(
        source="matricula.estudiante.codigo_estudiante",
        read_only=True,
    )
    estudiante_nombre = serializers.CharField(
        source="matricula.estudiante.perfil.user.get_full_name",
        read_only=True,
    )
    asignacion_curso_id = serializers.IntegerField(read_only=True)
    curso_nombre = serializers.CharField(
        source="asignacion_curso.curso.nombre",
        read_only=True,
    )
    seccion_nombre = serializers.CharField(
        source="asignacion_curso.seccion.nombre",
        read_only=True,
    )
    periodo_academico_id = serializers.IntegerField(read_only=True)
    periodo_nombre = serializers.CharField(
        source="periodo_academico.nombre",
        read_only=True,
    )
    criterio_calificacion_id = serializers.IntegerField(read_only=True)
    criterio_nombre = serializers.CharField(
        source="criterio_calificacion.nombre",
        read_only=True,
    )
    capacidad_nombre = serializers.CharField(
        source="criterio_calificacion.capacidad.nombre",
        read_only=True,
    )
    competencia_nombre = serializers.CharField(
        source="criterio_calificacion.capacidad.competencia.nombre",
        read_only=True,
    )
    valor_label = serializers.CharField(source="get_valor_display", read_only=True)

    class Meta:
        model = Calificacion
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
            "criterio_calificacion_id",
            "criterio_nombre",
            "capacidad_nombre",
            "competencia_nombre",
            "valor",
            "valor_label",
            "observacion",
        )
