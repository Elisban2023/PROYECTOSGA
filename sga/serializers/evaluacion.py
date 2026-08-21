from rest_framework import serializers

from sga.models import (
    Capacidad,
    Competencia,
    CriterioCalificacion,
    EstadoRegistro,
)


class CatalogoEvaluacionSerializerMixin:
    def validate_nombre(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )
        return value


class CompetenciaSerializer(
    CatalogoEvaluacionSerializerMixin,
    serializers.ModelSerializer,
):
    curso_label = serializers.StringRelatedField(source="curso", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Competencia
        fields = (
            "id",
            "curso",
            "curso_label",
            "nombre",
            "estado",
            "estado_label",
        )

    def validate(self, attrs):
        curso = attrs.get("curso", getattr(self.instance, "curso", None))
        if curso is not None and curso.estado != EstadoRegistro.ACTIVO:
            raise serializers.ValidationError(
                {"curso": "El curso seleccionado esta inactivo."}
            )
        return attrs


class CapacidadSerializer(
    CatalogoEvaluacionSerializerMixin,
    serializers.ModelSerializer,
):
    competencia_label = serializers.StringRelatedField(
        source="competencia",
        read_only=True,
    )
    curso_id = serializers.IntegerField(
        source="competencia.curso_id",
        read_only=True,
    )
    curso_label = serializers.StringRelatedField(
        source="competencia.curso",
        read_only=True,
    )
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Capacidad
        fields = (
            "id",
            "competencia",
            "competencia_label",
            "curso_id",
            "curso_label",
            "nombre",
            "estado",
            "estado_label",
        )

    def validate(self, attrs):
        competencia = attrs.get(
            "competencia",
            getattr(self.instance, "competencia", None),
        )
        if competencia is not None:
            if competencia.estado != EstadoRegistro.ACTIVO:
                raise serializers.ValidationError(
                    {"competencia": "La competencia seleccionada esta inactiva."}
                )
            if competencia.curso.estado != EstadoRegistro.ACTIVO:
                raise serializers.ValidationError(
                    {"competencia": "El curso de la competencia esta inactivo."}
                )
        return attrs


class CriterioCalificacionSerializer(
    CatalogoEvaluacionSerializerMixin,
    serializers.ModelSerializer,
):
    capacidad_label = serializers.StringRelatedField(
        source="capacidad",
        read_only=True,
    )
    competencia_id = serializers.IntegerField(
        source="capacidad.competencia_id",
        read_only=True,
    )
    competencia_label = serializers.StringRelatedField(
        source="capacidad.competencia",
        read_only=True,
    )
    curso_id = serializers.IntegerField(
        source="capacidad.competencia.curso_id",
        read_only=True,
    )
    curso_label = serializers.StringRelatedField(
        source="capacidad.competencia.curso",
        read_only=True,
    )
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = CriterioCalificacion
        fields = (
            "id",
            "capacidad",
            "capacidad_label",
            "competencia_id",
            "competencia_label",
            "curso_id",
            "curso_label",
            "nombre",
            "descripcion",
            "estado",
            "estado_label",
        )

    def validate_descripcion(self, value):
        value = (value or "").strip()
        if value and len(value) < 10:
            raise serializers.ValidationError(
                "La descripcion debe tener al menos 10 caracteres."
            )
        return value or None

    def validate(self, attrs):
        capacidad = attrs.get(
            "capacidad",
            getattr(self.instance, "capacidad", None),
        )
        if capacidad is not None:
            if capacidad.estado != EstadoRegistro.ACTIVO:
                raise serializers.ValidationError(
                    {"capacidad": "La capacidad seleccionada esta inactiva."}
                )
            if capacidad.competencia.estado != EstadoRegistro.ACTIVO:
                raise serializers.ValidationError(
                    {"capacidad": "La competencia de la capacidad esta inactiva."}
                )
            if capacidad.competencia.curso.estado != EstadoRegistro.ACTIVO:
                raise serializers.ValidationError(
                    {"capacidad": "El curso de la capacidad esta inactivo."}
                )
        return attrs
