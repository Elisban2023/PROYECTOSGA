from django.utils import timezone
from rest_framework import serializers

from sga.models import (
    EstadoAcademico,
    EstadoGeneral,
    EstadoIncidencia,
    EstadoRevisionIA,
    IncidenciaAcademica,
    ObservacionAcademica,
    RecomendacionIA,
)


class ObservacionAcademicaSerializer(serializers.ModelSerializer):
    estudiante_label = serializers.StringRelatedField(source="matricula.estudiante", read_only=True)
    estudiante_codigo = serializers.CharField(source="matricula.estudiante.codigo_estudiante", read_only=True)
    seccion_label = serializers.StringRelatedField(source="matricula.seccion", read_only=True)
    docente_label = serializers.StringRelatedField(source="docente", read_only=True)
    asignacion_curso_label = serializers.StringRelatedField(source="asignacion_curso", read_only=True)

    class Meta:
        model = ObservacionAcademica
        fields = (
            "id",
            "matricula",
            "estudiante_label",
            "estudiante_codigo",
            "seccion_label",
            "asignacion_curso",
            "asignacion_curso_label",
            "docente",
            "docente_label",
            "fecha",
            "categoria",
            "descripcion",
            "activo",
        )

    def validate_categoria(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("La categoria es obligatoria.")
        return value

    def validate_descripcion(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("La descripcion debe tener al menos 10 caracteres.")
        return value

    def validate_fecha(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("La fecha de observacion no puede ser futura.")
        return value

    def validate(self, attrs):
        matricula = attrs.get("matricula", getattr(self.instance, "matricula", None))
        docente = attrs.get("docente", getattr(self.instance, "docente", None))
        asignacion = attrs.get("asignacion_curso", getattr(self.instance, "asignacion_curso", None))

        if matricula is not None and matricula.estado != "ACTIVA":
            raise serializers.ValidationError({"matricula": "La matricula seleccionada no esta activa."})
        if docente is not None and not docente.perfil.user.is_active:
            raise serializers.ValidationError({"docente": "El docente seleccionado esta inactivo."})
        if asignacion is not None:
            if asignacion.estado != EstadoGeneral.ACTIVO:
                raise serializers.ValidationError({"asignacion_curso": "La asignacion de curso no esta activa."})
            if matricula is not None and asignacion.seccion_id != matricula.seccion_id:
                raise serializers.ValidationError({"asignacion_curso": "La asignacion no corresponde a la seccion de la matricula."})
            if matricula is not None and asignacion.anio_academico_id != matricula.anio_academico_id:
                raise serializers.ValidationError({"asignacion_curso": "La asignacion no corresponde al anio academico de la matricula."})
            if docente is not None and asignacion.docente_id != docente.id:
                raise serializers.ValidationError({"docente": "El docente no pertenece a la asignacion de curso."})
        return attrs


class IncidenciaAcademicaSerializer(serializers.ModelSerializer):
    estudiante_label = serializers.StringRelatedField(source="matricula.estudiante", read_only=True)
    estudiante_codigo = serializers.CharField(source="matricula.estudiante.codigo_estudiante", read_only=True)
    seccion_label = serializers.StringRelatedField(source="matricula.seccion", read_only=True)
    observacion_label = serializers.StringRelatedField(source="observacion", read_only=True)

    class Meta:
        model = IncidenciaAcademica
        fields = (
            "id",
            "matricula",
            "estudiante_label",
            "estudiante_codigo",
            "seccion_label",
            "observacion",
            "observacion_label",
            "tipo",
            "descripcion",
            "nivel",
            "estado",
            "fecha_registro",
            "fecha_cierre",
        )
        read_only_fields = ("fecha_cierre",)

    def validate_descripcion(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("La descripcion debe tener al menos 10 caracteres.")
        return value

    def validate_fecha_registro(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("La fecha de registro no puede ser futura.")
        return value

    def validate(self, attrs):
        matricula = attrs.get("matricula", getattr(self.instance, "matricula", None))
        observacion = attrs.get("observacion", getattr(self.instance, "observacion", None))
        estado = attrs.get("estado", getattr(self.instance, "estado", EstadoIncidencia.ABIERTA))
        fecha_registro = attrs.get("fecha_registro", getattr(self.instance, "fecha_registro", None))

        if matricula is not None and matricula.estado != "ACTIVA":
            raise serializers.ValidationError({"matricula": "La matricula seleccionada no esta activa."})
        if observacion is not None:
            if not observacion.activo:
                raise serializers.ValidationError({"observacion": "La observacion seleccionada esta inactiva."})
            if matricula is not None and observacion.matricula_id != matricula.id:
                raise serializers.ValidationError({"observacion": "La observacion no corresponde a la matricula seleccionada."})
        if estado == EstadoIncidencia.CERRADA and fecha_registro and fecha_registro > timezone.now():
            raise serializers.ValidationError({"fecha_registro": "No se puede cerrar una incidencia con fecha futura."})
        return attrs

    def create(self, validated_data):
        if validated_data.get("estado") == EstadoIncidencia.CERRADA:
            validated_data["fecha_cierre"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("estado") == EstadoIncidencia.CERRADA and instance.fecha_cierre is None:
            validated_data["fecha_cierre"] = timezone.now()
        if validated_data.get("estado") != EstadoIncidencia.CERRADA:
            validated_data["fecha_cierre"] = None
        return super().update(instance, validated_data)



class RecomendacionIASerializer(serializers.ModelSerializer):
    estudiante_label = serializers.StringRelatedField(source="matricula.estudiante", read_only=True)
    estudiante_codigo = serializers.CharField(source="matricula.estudiante.codigo_estudiante", read_only=True)
    seccion_label = serializers.StringRelatedField(source="matricula.seccion", read_only=True)
    periodo_academico_label = serializers.StringRelatedField(source="periodo_academico", read_only=True)
    docente_revisor_label = serializers.StringRelatedField(source="revisado_por_docente", read_only=True)

    class Meta:
        model = RecomendacionIA
        fields = (
            "id",
            "matricula",
            "estudiante_label",
            "estudiante_codigo",
            "seccion_label",
            "periodo_academico",
            "periodo_academico_label",
            "revisado_por_docente",
            "docente_revisor_label",
            "resumen_contexto",
            "texto_generado",
            "texto_revisado",
            "estado_revision",
            "fecha_generacion",
            "fecha_revision",
            "activo",
        )
        read_only_fields = ("fecha_revision",)

    def validate_resumen_contexto(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("El resumen de contexto debe tener al menos 10 caracteres.")
        return value

    def validate_texto_generado(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("El texto generado debe tener al menos 10 caracteres.")
        return value

    def validate_texto_revisado(self, value):
        if value is None:
            return value
        value = value.strip()
        if value and len(value) < 10:
            raise serializers.ValidationError("El texto revisado debe tener al menos 10 caracteres.")
        return value

    def validate_fecha_generacion(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("La fecha de generacion no puede ser futura.")
        return value

    def validate(self, attrs):
        matricula = attrs.get("matricula", getattr(self.instance, "matricula", None))
        periodo = attrs.get("periodo_academico", getattr(self.instance, "periodo_academico", None))
        docente = attrs.get("revisado_por_docente", getattr(self.instance, "revisado_por_docente", None))
        estado = attrs.get("estado_revision", getattr(self.instance, "estado_revision", EstadoRevisionIA.PENDIENTE))
        texto_revisado = attrs.get("texto_revisado", getattr(self.instance, "texto_revisado", None))

        if matricula is not None and matricula.estado != "ACTIVA":
            raise serializers.ValidationError({"matricula": "La matricula seleccionada no esta activa."})
        if periodo is not None:
            if periodo.estado == EstadoAcademico.INACTIVO:
                raise serializers.ValidationError({"periodo_academico": "El periodo academico seleccionado esta inactivo."})
            if matricula is not None and periodo.anio_academico_id != matricula.anio_academico_id:
                raise serializers.ValidationError({"periodo_academico": "El periodo no pertenece al anio academico de la matricula."})
        if docente is not None and not docente.perfil.user.is_active:
            raise serializers.ValidationError({"revisado_por_docente": "El docente revisor esta inactivo."})
        if estado in {EstadoRevisionIA.APROBADA, EstadoRevisionIA.RECHAZADA, EstadoRevisionIA.EDITADA} and docente is None:
            raise serializers.ValidationError({"revisado_por_docente": "Debe indicar el docente que revisa la recomendacion."})
        if estado == EstadoRevisionIA.EDITADA and not texto_revisado:
            raise serializers.ValidationError({"texto_revisado": "Debe registrar el texto revisado cuando el estado es EDITADA."})
        return attrs

    def create(self, validated_data):
        if validated_data.get("estado_revision") in {
            EstadoRevisionIA.APROBADA,
            EstadoRevisionIA.RECHAZADA,
            EstadoRevisionIA.EDITADA,
        }:
            validated_data["fecha_revision"] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        estado = validated_data.get("estado_revision", instance.estado_revision)
        if estado in {EstadoRevisionIA.APROBADA, EstadoRevisionIA.RECHAZADA, EstadoRevisionIA.EDITADA}:
            if instance.fecha_revision is None:
                validated_data["fecha_revision"] = timezone.now()
        else:
            validated_data["fecha_revision"] = None
        return super().update(instance, validated_data)


class RecomendacionIARevisionSerializer(serializers.Serializer):
    docente = serializers.IntegerField(required=True)
    texto_revisado = serializers.CharField(required=False, allow_blank=True)
