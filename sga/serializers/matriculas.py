from django.utils import timezone
from rest_framework import serializers

from sga.models import EstadoAcademico, EstadoRegistro, Matricula


class MatriculaSerializer(serializers.ModelSerializer):
    estudiante_label = serializers.StringRelatedField(source="estudiante", read_only=True)
    estudiante_codigo = serializers.CharField(source="estudiante.codigo_estudiante", read_only=True)
    estudiante_nombre = serializers.CharField(source="estudiante.perfil.user.get_full_name", read_only=True)
    seccion_label = serializers.StringRelatedField(source="seccion", read_only=True)
    grado_label = serializers.StringRelatedField(source="seccion.grado", read_only=True)
    anio_academico_label = serializers.StringRelatedField(source="anio_academico", read_only=True)

    class Meta:
        model = Matricula
        fields = (
            "id",
            "estudiante",
            "estudiante_label",
            "estudiante_codigo",
            "estudiante_nombre",
            "seccion",
            "seccion_label",
            "grado_label",
            "anio_academico",
            "anio_academico_label",
            "fecha_matricula",
            "estado",
        )
        validators = []

    def validate_fecha_matricula(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("La fecha de matricula no puede ser futura.")
        return value

    def validate(self, attrs):
        estudiante = attrs.get("estudiante", getattr(self.instance, "estudiante", None))
        seccion = attrs.get("seccion", getattr(self.instance, "seccion", None))
        anio_academico = attrs.get("anio_academico", getattr(self.instance, "anio_academico", None))
        fecha_matricula = attrs.get("fecha_matricula", getattr(self.instance, "fecha_matricula", None))

        if estudiante is not None and not estudiante.perfil.user.is_active:
            raise serializers.ValidationError({"estudiante": "El estudiante seleccionado esta inactivo."})
        if seccion is not None and seccion.estado == EstadoRegistro.INACTIVO:
            raise serializers.ValidationError({"seccion": "La seccion seleccionada esta inactiva."})
        if seccion is not None and seccion.grado.estado == EstadoRegistro.INACTIVO:
            raise serializers.ValidationError({"seccion": "El grado de la seccion seleccionada esta inactivo."})
        if anio_academico is not None and anio_academico.estado == EstadoAcademico.INACTIVO:
            raise serializers.ValidationError({"anio_academico": "El anio academico seleccionado esta inactivo."})
        if fecha_matricula and anio_academico and not (anio_academico.fecha_inicio <= fecha_matricula <= anio_academico.fecha_fin):
            raise serializers.ValidationError({"fecha_matricula": "La fecha de matricula debe estar dentro del anio academico."})

        queryset = Matricula.objects.filter(estudiante=estudiante, anio_academico=anio_academico)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if estudiante is not None and anio_academico is not None and queryset.exists():
            raise serializers.ValidationError("Este estudiante ya tiene una matricula registrada para este anio academico.")
        return attrs
