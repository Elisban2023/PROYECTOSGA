from rest_framework import serializers

from sga.models import EstadoMatricula, VinculoApoderado


class ApoderadoEstudianteSerializer(serializers.ModelSerializer):
    estudiante_id = serializers.IntegerField(read_only=True)
    codigo_estudiante = serializers.CharField(source="estudiante.codigo_estudiante", read_only=True)
    estudiante_nombre = serializers.CharField(source="estudiante.perfil.user.get_full_name", read_only=True)
    matriculas_activas = serializers.SerializerMethodField()
    parentesco_label = serializers.CharField(source="get_parentesco_display", read_only=True)

    class Meta:
        model = VinculoApoderado
        fields = ("id", "estudiante_id", "codigo_estudiante", "estudiante_nombre", "parentesco", "parentesco_label", "es_principal", "matriculas_activas")

    def get_matriculas_activas(self, obj):
        return [
            {"id": matricula.id, "anio_academico": matricula.anio_academico.anio, "grado_nombre": matricula.seccion.grado.nombre, "seccion_nombre": matricula.seccion.nombre}
            for matricula in obj.estudiante.matriculas.all()
            if matricula.estado == EstadoMatricula.ACTIVA
        ]
