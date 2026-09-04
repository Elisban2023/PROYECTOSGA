from rest_framework import serializers

from sga.models import TipoCorreo


class ComunicacionDocenteSolicitudSerializer(serializers.Serializer):
    matricula_id = serializers.IntegerField(min_value=1)
    asignacion_curso_id = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(
        choices=(
            TipoCorreo.CALIFICACIONES,
            TipoCorreo.RECOMENDACION,
            TipoCorreo.INCIDENCIA,
            TipoCorreo.ASISTENCIA,
            TipoCorreo.SEGUIMIENTO,
        )
    )
    periodo_academico_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    recomendacion_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    incidencia_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    mensaje_adicional = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        tipo = attrs["tipo"]
        if tipo == TipoCorreo.RECOMENDACION and not attrs.get("recomendacion_id"):
            raise serializers.ValidationError(
                {"recomendacion_id": "Debe seleccionar una recomendacion aprobada o editada."}
            )
        if tipo == TipoCorreo.INCIDENCIA and not attrs.get("incidencia_id"):
            raise serializers.ValidationError(
                {"incidencia_id": "Debe seleccionar la incidencia que se comunicara."}
            )
        if tipo != TipoCorreo.RECOMENDACION and attrs.get("recomendacion_id"):
            raise serializers.ValidationError(
                {"recomendacion_id": "Este campo solo corresponde a comunicaciones de recomendacion."}
            )
        if tipo != TipoCorreo.INCIDENCIA and attrs.get("incidencia_id"):
            raise serializers.ValidationError(
                {"incidencia_id": "Este campo solo corresponde a comunicaciones de incidencia."}
            )
        return attrs
