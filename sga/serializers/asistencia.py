from rest_framework import serializers

from sga.models import Asistencia, EstadoAsistencia


class EstadoAsistenciaSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=EstadoAsistencia.choices)
    justificacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=500,
    )

    def validate_justificacion(self, value):
        return (value or "").strip() or None

    def validate(self, attrs):
        if (
            attrs.get("estado") == EstadoAsistencia.JUSTIFICADA
            and not attrs.get("justificacion")
        ):
            raise serializers.ValidationError(
                {"justificacion": "La asistencia justificada requiere una justificacion."}
            )
        return attrs


class RegistroAsistenciaItemSerializer(EstadoAsistenciaSerializer):
    matricula = serializers.IntegerField(min_value=1)


class RegistrarAsistenciasSerializer(serializers.Serializer):
    asignacion_curso = serializers.IntegerField(min_value=1)
    fecha = serializers.DateField()
    registros = RegistroAsistenciaItemSerializer(many=True, allow_empty=False)

    def validate_registros(self, value):
        matricula_ids = [registro["matricula"] for registro in value]
        if len(matricula_ids) != len(set(matricula_ids)):
            raise serializers.ValidationError(
                "No puede registrar la asistencia de una matricula mas de una vez."
            )
        return value


class ActualizarAsistenciaSerializer(EstadoAsistenciaSerializer):
    pass


class AsistenciaDocenteSerializer(serializers.ModelSerializer):
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
    grado_nombre = serializers.CharField(
        source="asignacion_curso.seccion.grado.nombre",
        read_only=True,
    )
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Asistencia
        fields = (
            "id",
            "matricula_id",
            "estudiante_id",
            "estudiante_codigo",
            "estudiante_nombre",
            "asignacion_curso_id",
            "curso_nombre",
            "seccion_nombre",
            "grado_nombre",
            "fecha",
            "estado",
            "estado_label",
            "justificacion",
        )
