from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AnioAcademico,
    AsignacionCurso,
    Curso,
    Grado,
    PeriodoAcademico,
    Seccion,
)


User = get_user_model()


class UserMeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    perfil_id = serializers.IntegerField(source="perfil.id", read_only=True)
    estudiante_id = serializers.IntegerField(source="perfil.estudiante.id", read_only=True)
    docente_id = serializers.IntegerField(source="perfil.docente.id", read_only=True)
    apoderado_id = serializers.IntegerField(source="perfil.apoderado.id", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "is_superuser",
            "groups",
            "perfil_id",
            "estudiante_id",
            "docente_id",
            "apoderado_id",
        )
        read_only_fields = fields


class AnioAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnioAcademico
        fields = (
            "id",
            "anio",
            "fecha_inicio",
            "fecha_fin",
            "estado",
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
        )


class GradoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grado
        fields = (
            "id",
            "nombre",
            "nivel",
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
