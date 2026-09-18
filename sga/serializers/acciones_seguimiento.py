from django.utils import timezone
from rest_framework import serializers

from sga.models import (
    AccionSeguimiento,
    ActualizacionAccionSeguimiento,
    EstadoAccionSeguimiento,
    PrioridadNotificacion,
    ResponsableAccionSeguimiento,
    TipoAccionSeguimiento,
    TipoActualizacionSeguimiento,
)


class ActualizacionAccionSeguimientoSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()
    autor_username = serializers.CharField(source="autor.username", read_only=True)
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = ActualizacionAccionSeguimiento
        fields = (
            "id",
            "autor",
            "autor_nombre",
            "autor_username",
            "tipo",
            "tipo_label",
            "comentario",
            "progreso",
            "creado_en",
        )
        read_only_fields = fields

    def get_autor_nombre(self, obj) -> str:
        return obj.autor.get_full_name().strip() or obj.autor.username


class AccionSeguimientoSerializer(serializers.ModelSerializer):
    estudiante_id = serializers.IntegerField(source="matricula.estudiante_id", read_only=True)
    estudiante_codigo = serializers.CharField(
        source="matricula.estudiante.codigo_estudiante",
        read_only=True,
    )
    estudiante_nombre = serializers.SerializerMethodField()
    curso_nombre = serializers.CharField(source="asignacion_curso.curso.nombre", read_only=True)
    grado_nombre = serializers.CharField(
        source="asignacion_curso.seccion.grado.nombre",
        read_only=True,
    )
    seccion_nombre = serializers.CharField(
        source="asignacion_curso.seccion.nombre",
        read_only=True,
    )
    periodo_nombre = serializers.CharField(
        source="periodo_academico.nombre",
        read_only=True,
        allow_null=True,
    )
    docente_nombre = serializers.SerializerMethodField()
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)
    responsable_label = serializers.CharField(source="get_responsable_display", read_only=True)
    prioridad_label = serializers.CharField(source="get_prioridad_display", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)
    vencida = serializers.SerializerMethodField()
    actualizaciones = ActualizacionAccionSeguimientoSerializer(many=True, read_only=True)

    class Meta:
        model = AccionSeguimiento
        fields = (
            "id",
            "matricula",
            "estudiante_id",
            "estudiante_codigo",
            "estudiante_nombre",
            "asignacion_curso",
            "curso_nombre",
            "grado_nombre",
            "seccion_nombre",
            "periodo_academico",
            "periodo_nombre",
            "docente",
            "docente_nombre",
            "incidencia",
            "recomendacion",
            "tipo",
            "tipo_label",
            "responsable",
            "responsable_label",
            "prioridad",
            "prioridad_label",
            "titulo",
            "descripcion",
            "estado",
            "estado_label",
            "fecha_limite",
            "fecha_completada",
            "resultado",
            "visible_estudiante",
            "visible_apoderado",
            "vencida",
            "actualizaciones",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = fields

    def get_estudiante_nombre(self, obj) -> str:
        usuario = obj.matricula.estudiante.perfil.user
        return usuario.get_full_name().strip() or usuario.username

    def get_docente_nombre(self, obj) -> str:
        usuario = obj.docente.perfil.user
        return usuario.get_full_name().strip() or usuario.username

    def get_vencida(self, obj) -> bool:
        return bool(
            obj.fecha_limite
            and obj.fecha_limite < timezone.localdate()
            and obj.estado
            not in (EstadoAccionSeguimiento.COMPLETADA, EstadoAccionSeguimiento.CANCELADA)
        )


class AccionSeguimientoCrearSerializer(serializers.Serializer):
    matricula_id = serializers.IntegerField(min_value=1)
    asignacion_curso_id = serializers.IntegerField(min_value=1)
    periodo_academico_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    incidencia_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    recomendacion_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    tipo = serializers.ChoiceField(choices=TipoAccionSeguimiento.choices)
    responsable = serializers.ChoiceField(choices=ResponsableAccionSeguimiento.choices)
    prioridad = serializers.ChoiceField(
        choices=PrioridadNotificacion.choices,
        default=PrioridadNotificacion.NORMAL,
    )
    titulo = serializers.CharField(min_length=5, max_length=150, trim_whitespace=True)
    descripcion = serializers.CharField(min_length=10, max_length=2000, trim_whitespace=True)
    fecha_limite = serializers.DateField()
    visible_estudiante = serializers.BooleanField(default=True)
    visible_apoderado = serializers.BooleanField(default=True)
    notificar_destinatarios = serializers.BooleanField(default=True)

    def validate_fecha_limite(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError("La fecha limite no puede estar en el pasado.")
        return value

    def validate(self, attrs):
        responsable = attrs["responsable"]
        if responsable in (
            ResponsableAccionSeguimiento.ESTUDIANTE,
            ResponsableAccionSeguimiento.COMPARTIDA,
        ) and not attrs["visible_estudiante"]:
            raise serializers.ValidationError(
                {"visible_estudiante": "La accion debe ser visible para el estudiante responsable."}
            )
        if responsable in (
            ResponsableAccionSeguimiento.APODERADO,
            ResponsableAccionSeguimiento.COMPARTIDA,
        ) and not attrs["visible_apoderado"]:
            raise serializers.ValidationError(
                {"visible_apoderado": "La accion debe ser visible para el apoderado responsable."}
            )
        return attrs


class AccionSeguimientoActualizarSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=TipoAccionSeguimiento.choices, required=False)
    responsable = serializers.ChoiceField(
        choices=ResponsableAccionSeguimiento.choices,
        required=False,
    )
    prioridad = serializers.ChoiceField(choices=PrioridadNotificacion.choices, required=False)
    titulo = serializers.CharField(
        min_length=5,
        max_length=150,
        trim_whitespace=True,
        required=False,
    )
    descripcion = serializers.CharField(
        min_length=10,
        max_length=3000,
        trim_whitespace=True,
        required=False,
    )
    estado = serializers.ChoiceField(choices=EstadoAccionSeguimiento.choices, required=False)
    fecha_limite = serializers.DateField(required=False, allow_null=True)
    resultado = serializers.CharField(
        min_length=10,
        max_length=3000,
        trim_whitespace=True,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    visible_estudiante = serializers.BooleanField(required=False)
    visible_apoderado = serializers.BooleanField(required=False)

    def validate_fecha_limite(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError("La fecha limite no puede estar en el pasado.")
        return value


class ActualizacionAccionCrearSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(
        choices=TipoActualizacionSeguimiento.choices,
        default=TipoActualizacionSeguimiento.COMENTARIO,
    )
    comentario = serializers.CharField(
        min_length=5,
        max_length=2000,
        trim_whitespace=True,
    )
    progreso = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        if attrs["tipo"] == TipoActualizacionSeguimiento.AVANCE and attrs.get("progreso") is None:
            raise serializers.ValidationError(
                {"progreso": "Indique el porcentaje cuando registra un avance."}
            )
        return attrs
