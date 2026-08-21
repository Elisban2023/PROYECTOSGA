from rest_framework import serializers

from sga.models import AsignacionCurso


class EstudianteCursoSerializer(serializers.ModelSerializer):
    curso_id = serializers.IntegerField(read_only=True)
    curso_nombre = serializers.CharField(source="curso.nombre", read_only=True)
    seccion_id = serializers.IntegerField(read_only=True)
    seccion_nombre = serializers.CharField(source="seccion.nombre", read_only=True)
    grado_nombre = serializers.CharField(source="seccion.grado.nombre", read_only=True)
    anio_academico_id = serializers.IntegerField(read_only=True)
    anio_academico = serializers.IntegerField(source="anio_academico.anio", read_only=True)
    docente_id = serializers.IntegerField(read_only=True)
    docente_nombre = serializers.CharField(source="docente.perfil.user.get_full_name", read_only=True)

    class Meta:
        model = AsignacionCurso
        fields = (
            "id", "curso_id", "curso_nombre", "seccion_id", "seccion_nombre",
            "grado_nombre", "anio_academico_id", "anio_academico", "docente_id", "docente_nombre",
        )
