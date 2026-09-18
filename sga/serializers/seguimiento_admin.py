from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from sga.models import AsignacionCurso, Docente


class SeguimientoAsignacionAdminSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source="curso.nombre", read_only=True)
    grado_nombre = serializers.CharField(source="seccion.grado.nombre", read_only=True)
    seccion_nombre = serializers.CharField(source="seccion.nombre", read_only=True)
    anio = serializers.IntegerField(source="anio_academico.anio", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = AsignacionCurso
        fields = (
            "id",
            "curso_nombre",
            "grado_nombre",
            "seccion_nombre",
            "anio_academico_id",
            "anio",
            "estado",
            "estado_label",
        )


class SeguimientoDocenteResumenSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="perfil.user_id", read_only=True)
    nombre = serializers.CharField(source="perfil.user.get_full_name", read_only=True)
    username = serializers.CharField(source="perfil.user.username", read_only=True)
    email = serializers.EmailField(source="perfil.user.email", read_only=True)
    activo = serializers.BooleanField(source="perfil.user.is_active", read_only=True)
    asignaciones_activas = serializers.IntegerField(read_only=True)
    observaciones_total = serializers.IntegerField(read_only=True)
    incidencias_total = serializers.IntegerField(read_only=True)
    incidencias_abiertas = serializers.IntegerField(read_only=True)
    recomendaciones_total = serializers.IntegerField(read_only=True)
    recomendaciones_pendientes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Docente
        fields = (
            "id",
            "user_id",
            "nombre",
            "username",
            "email",
            "activo",
            "asignaciones_activas",
            "observaciones_total",
            "incidencias_total",
            "incidencias_abiertas",
            "recomendaciones_total",
            "recomendaciones_pendientes",
        )


class SeguimientoDocenteDetalleSerializer(SeguimientoDocenteResumenSerializer):
    asignaciones = serializers.SerializerMethodField()

    class Meta(SeguimientoDocenteResumenSerializer.Meta):
        fields = SeguimientoDocenteResumenSerializer.Meta.fields + ("asignaciones",)

    @extend_schema_field(SeguimientoAsignacionAdminSerializer(many=True))
    def get_asignaciones(self, obj):
        asignaciones = getattr(obj, "asignaciones_seguimiento", [])
        return SeguimientoAsignacionAdminSerializer(asignaciones, many=True).data
