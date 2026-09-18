from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from sga.models import (
    BackupBaseDatos,
    EstadoJustificacion,
    JustificacionInasistencia,
)


class SolicitarCargaJustificacionSerializer(serializers.Serializer):
    asistencia_id = serializers.IntegerField(min_value=1)
    nombre_archivo = serializers.CharField(min_length=3, max_length=255)
    mime_type = serializers.ChoiceField(
        choices=("application/pdf", "image/jpeg", "image/png")
    )
    tamano = serializers.IntegerField(
        min_value=1,
        max_value=settings.AWS_S3_MAX_JUSTIFICACION_BYTES,
    )
    motivo = serializers.CharField(min_length=10, max_length=2000, trim_whitespace=True)


class ConfirmarCargaSerializer(serializers.Serializer):
    confirmar = serializers.BooleanField()

    def validate_confirmar(self, value):
        if not value:
            raise serializers.ValidationError("Debe confirmar que la carga finalizo.")
        return value


class RevisarJustificacionSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(
        choices=(EstadoJustificacion.APROBADA, EstadoJustificacion.RECHAZADA)
    )
    comentario = serializers.CharField(
        min_length=10,
        max_length=500,
        trim_whitespace=True,
    )


class JustificacionInasistenciaSerializer(serializers.ModelSerializer):
    estudiante_id = serializers.IntegerField(source="asistencia.matricula.estudiante_id", read_only=True)
    estudiante_nombre = serializers.SerializerMethodField()
    asignacion_curso_id = serializers.IntegerField(source="asistencia.asignacion_curso_id", read_only=True)
    curso_nombre = serializers.CharField(source="asistencia.asignacion_curso.curso.nombre", read_only=True)
    grado_nombre = serializers.CharField(source="asistencia.matricula.seccion.grado.nombre", read_only=True)
    seccion_nombre = serializers.CharField(source="asistencia.matricula.seccion.nombre", read_only=True)
    anio_academico = serializers.IntegerField(source="asistencia.matricula.anio_academico.anio", read_only=True)
    fecha_inasistencia = serializers.DateField(source="asistencia.fecha", read_only=True)
    estado_asistencia = serializers.CharField(source="asistencia.estado", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)
    apoderado_nombre = serializers.SerializerMethodField()
    archivo_nombre = serializers.CharField(source="archivo.nombre_original", read_only=True)
    archivo_mime_type = serializers.CharField(source="archivo.mime_type", read_only=True)
    archivo_tamano = serializers.IntegerField(source="archivo.tamano", read_only=True)
    archivo_disponible = serializers.SerializerMethodField()
    revisado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = JustificacionInasistencia
        fields = (
            "id",
            "asistencia",
            "estudiante_id",
            "estudiante_nombre",
            "asignacion_curso_id",
            "curso_nombre",
            "grado_nombre",
            "seccion_nombre",
            "anio_academico",
            "fecha_inasistencia",
            "estado_asistencia",
            "apoderado",
            "apoderado_nombre",
            "motivo",
            "estado",
            "estado_label",
            "archivo_nombre",
            "archivo_mime_type",
            "archivo_tamano",
            "archivo_disponible",
            "comentario_revision",
            "revisado_por_nombre",
            "fecha_solicitud",
            "fecha_revision",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_estudiante_nombre(self, obj):
        user = obj.asistencia.matricula.estudiante.perfil.user
        return user.get_full_name().strip() or user.username

    @extend_schema_field(serializers.CharField())
    def get_apoderado_nombre(self, obj):
        user = obj.apoderado.perfil.user
        return user.get_full_name().strip() or user.username

    @extend_schema_field(serializers.BooleanField())
    def get_archivo_disponible(self, obj):
        return obj.archivo.estado == "DISPONIBLE"

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_revisado_por_nombre(self, obj):
        if not obj.revisado_por_id:
            return None
        user = obj.revisado_por.perfil.user
        return user.get_full_name().strip() or user.username


class CrearBackupSerializer(serializers.Serializer):
    confirmacion = serializers.CharField()

    def validate_confirmacion(self, value):
        if value != "CREAR BACKUP":
            raise serializers.ValidationError('Escriba exactamente "CREAR BACKUP".')
        return value


class RestaurarBackupSerializer(serializers.Serializer):
    confirmacion = serializers.CharField()

    def validate_confirmacion(self, value):
        if value != "RESTAURAR BACKUP":
            raise serializers.ValidationError('Escriba exactamente "RESTAURAR BACKUP".')
        return value


class EliminarBackupSerializer(serializers.Serializer):
    confirmacion = serializers.CharField()

    def validate_confirmacion(self, value):
        if value != "ELIMINAR BACKUP":
            raise serializers.ValidationError('Escriba exactamente "ELIMINAR BACKUP".')
        return value


class BackupBaseDatosSerializer(serializers.ModelSerializer):
    estado_url = serializers.SerializerMethodField()
    iniciado_por_username = serializers.CharField(source="iniciado_por.username", read_only=True)
    restaurado_por_username = serializers.CharField(source="restaurado_por.username", read_only=True)
    archivo_nombre = serializers.CharField(source="archivo.nombre_original", read_only=True)
    tamano = serializers.IntegerField(source="archivo.tamano", read_only=True)
    sha256 = serializers.CharField(source="archivo.sha256", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = BackupBaseDatos
        fields = (
            "id",
            "tipo",
            "tipo_label",
            "estado",
            "estado_label",
            "iniciado_por_username",
            "restaurado_por_username",
            "fecha_creacion",
            "fecha_finalizacion",
            "fecha_restauracion",
            "manifiesto",
            "archivo_nombre",
            "tamano",
            "sha256",
            "detalle_error",
            "estado_url",
        )
        read_only_fields = fields

    def get_estado_url(self, obj) -> str:
        return f"/api/administracion/backups/{obj.id}/"
