from rest_framework import serializers

from sga.models import ObservacionAcademica


class DatosObservacionDocenteSerializer(serializers.Serializer):
    fecha = serializers.DateTimeField()
    categoria = serializers.CharField(max_length=100)
    descripcion = serializers.CharField()

    def validate_categoria(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("La categoria debe tener al menos 3 caracteres.")
        return value

    def validate_descripcion(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError(
                "La descripcion debe tener al menos 10 caracteres."
            )
        return value


class RegistrarObservacionDocenteSerializer(DatosObservacionDocenteSerializer):
    matricula = serializers.IntegerField(min_value=1)
    asignacion_curso = serializers.IntegerField(min_value=1)


class ActualizarObservacionDocenteSerializer(DatosObservacionDocenteSerializer):
    fecha = serializers.DateTimeField(required=False)
    categoria = serializers.CharField(max_length=100, required=False)
    descripcion = serializers.CharField(required=False)


class ObservacionDocenteSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = ObservacionAcademica
        fields = (
            "id",
            "matricula_id",
            "estudiante_id",
            "estudiante_codigo",
            "estudiante_nombre",
            "asignacion_curso_id",
            "curso_nombre",
            "seccion_nombre",
            "fecha",
            "categoria",
            "descripcion",
            "activo",
        )
