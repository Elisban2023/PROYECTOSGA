from rest_framework import serializers


class ReportePDFQuerySerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(
        choices=(
            "dashboard",
            "resumen",
            "academico",
            "matriculas",
            "incidencias",
            "notificaciones",
            "asistencias",
            "calificaciones",
            "seguimiento",
        ),
        default="dashboard",
    )
    anio_academico = serializers.IntegerField(min_value=1, required=False)
    periodo_academico = serializers.IntegerField(min_value=1, required=False)
    grado = serializers.IntegerField(min_value=1, required=False)
    seccion = serializers.IntegerField(min_value=1, required=False)
    docente = serializers.IntegerField(min_value=1, required=False)
    asignacion_curso = serializers.IntegerField(min_value=1, required=False)
    estudiante = serializers.IntegerField(min_value=1, required=False)
    estado = serializers.CharField(max_length=30, required=False)
    nivel = serializers.CharField(max_length=30, required=False)
    estado_envio = serializers.CharField(max_length=30, required=False)
