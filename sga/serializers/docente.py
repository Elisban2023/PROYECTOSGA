from rest_framework import serializers

from sga.models import AsignacionCurso, Matricula


class DocenteCursoSerializer(serializers.ModelSerializer):
    curso_id = serializers.IntegerField(read_only=True)
    curso_nombre = serializers.CharField(source="curso.nombre", read_only=True)
    curso_descripcion = serializers.CharField(
        source="curso.descripcion",
        read_only=True,
        allow_null=True,
    )
    grado_id = serializers.IntegerField(source="seccion.grado_id", read_only=True)
    grado_nombre = serializers.CharField(
        source="seccion.grado.nombre",
        read_only=True,
    )
    grado_nivel = serializers.CharField(
        source="seccion.grado.nivel",
        read_only=True,
    )
    seccion_id = serializers.IntegerField(read_only=True)
    seccion_nombre = serializers.CharField(source="seccion.nombre", read_only=True)
    anio_academico_id = serializers.IntegerField(read_only=True)
    anio_academico = serializers.IntegerField(
        source="anio_academico.anio",
        read_only=True,
    )
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)
    estudiantes_matriculados = serializers.IntegerField(read_only=True)

    class Meta:
        model = AsignacionCurso
        fields = (
            "id",
            "curso_id",
            "curso_nombre",
            "curso_descripcion",
            "grado_id",
            "grado_nombre",
            "grado_nivel",
            "seccion_id",
            "seccion_nombre",
            "anio_academico_id",
            "anio_academico",
            "estado",
            "estado_label",
            "estudiantes_matriculados",
        )


class DocenteEstudianteCursoSerializer(serializers.ModelSerializer):
    estudiante_id = serializers.IntegerField(read_only=True)
    codigo_estudiante = serializers.CharField(
        source="estudiante.codigo_estudiante",
        read_only=True,
    )
    estudiante_nombre = serializers.CharField(
        source="estudiante.perfil.user.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Matricula
        fields = (
            "id",
            "estudiante_id",
            "codigo_estudiante",
            "estudiante_nombre",
            "fecha_matricula",
        )
