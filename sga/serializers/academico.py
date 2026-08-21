from rest_framework import serializers

from sga.models import (
    AnioAcademico,
    AsignacionCurso,
    Curso,
    Grado,
    PeriodoAcademico,
    Seccion,
)


class AnioAcademicoSerializer(serializers.ModelSerializer):
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = AnioAcademico
        fields = (
            "id",
            "anio",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "estado_label",
        )


class PeriodoAcademicoSerializer(serializers.ModelSerializer):
    anio_academico_label = serializers.StringRelatedField(source="anio_academico", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = PeriodoAcademico
        fields = (
            "id",
            "anio_academico",
            "anio_academico_label",
            "nombre",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "estado_label",
        )


class GradoSerializer(serializers.ModelSerializer):
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Grado
        fields = (
            "id",
            "nombre",
            "estado",
            "estado_label",
        )


class SeccionSerializer(serializers.ModelSerializer):
    grado_label = serializers.StringRelatedField(source="grado", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Seccion
        fields = (
            "id",
            "grado",
            "grado_label",
            "nombre",
            "estado",
            "estado_label",
        )


class CursoSerializer(serializers.ModelSerializer):
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Curso
        fields = (
            "id",
            "nombre",
            "descripcion",
            "estado",
            "estado_label",
        )


class AsignacionCursoSerializer(serializers.ModelSerializer):
    curso_label = serializers.StringRelatedField(source="curso", read_only=True)
    docente_label = serializers.StringRelatedField(source="docente", read_only=True)
    seccion_label = serializers.StringRelatedField(source="seccion", read_only=True)
    anio_academico_label = serializers.StringRelatedField(source="anio_academico", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = AsignacionCurso
        fields = (
            "id",
            "curso",
            "curso_label",
            "docente",
            "docente_label",
            "seccion",
            "seccion_label",
            "anio_academico",
            "anio_academico_label",
            "estado",
            "estado_label",
        )
