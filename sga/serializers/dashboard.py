from rest_framework import serializers


class DashboardFiltrosSerializer(serializers.Serializer):
    anio_academico = serializers.IntegerField(min_value=1, required=False)
    periodo_academico = serializers.IntegerField(min_value=1, required=False)
    grado = serializers.IntegerField(min_value=1, required=False)
    seccion = serializers.IntegerField(min_value=1, required=False)
    docente = serializers.IntegerField(min_value=1, required=False)
    asignacion_curso = serializers.IntegerField(min_value=1, required=False)
    estudiante = serializers.IntegerField(min_value=1, required=False)
