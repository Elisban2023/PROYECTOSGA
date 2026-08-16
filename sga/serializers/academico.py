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
    class Meta:
        model = AnioAcademico
        fields = (
            "id",
            "anio",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "activo",
        )


class PeriodoAcademicoSerializer(serializers.ModelSerializer):
    anio_academico_label = serializers.StringRelatedField(source="anio_academico", read_only=True)

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
            "activo",
        )


class GradoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grado
        fields = (
            "id",
            "nombre",
            "nivel",
            "activo",
        )


class SeccionSerializer(serializers.ModelSerializer):
    grado_label = serializers.StringRelatedField(source="grado", read_only=True)

    class Meta:
        model = Seccion
        fields = (
            "id",
            "grado",
            "grado_label",
            "nombre",
            "activo",
        )


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = (
            "id",
            "nombre",
            "descripcion",
            "estado",
        )


class AsignacionCursoSerializer(serializers.ModelSerializer):
    curso_label = serializers.StringRelatedField(source="curso", read_only=True)
    docente_label = serializers.StringRelatedField(source="docente", read_only=True)
    seccion_label = serializers.StringRelatedField(source="seccion", read_only=True)
    anio_academico_label = serializers.StringRelatedField(source="anio_academico", read_only=True)

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
        )
