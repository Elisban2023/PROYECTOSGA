from rest_framework import serializers

from sga.models import AnioAcademico, ConfiguracionInstitucional


class ConfiguracionInstitucionalSerializer(serializers.ModelSerializer):
    anio_academico_activo_label = serializers.StringRelatedField(source="anio_academico_activo", read_only=True)

    class Meta:
        model = ConfiguracionInstitucional
        fields = (
            "id",
            "nombre_institucion",
            "codigo_modular",
            "direccion",
            "telefono",
            "email",
            "director",
            "logo_url",
            "zona_horaria",
            "anio_academico_activo",
            "anio_academico_activo_label",
            "activo",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("id", "creado_en", "actualizado_en", "anio_academico_activo_label")

    def validate_nombre_institucion(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("El nombre de la institucion debe tener al menos 3 caracteres.")
        return value

    def validate_codigo_modular(self, value):
        value = (value or "").strip()
        if value and (not value.isdigit() or len(value) > 30):
            raise serializers.ValidationError("El codigo modular debe contener solo digitos y maximo 30 caracteres.")
        return value

    def validate_telefono(self, value):
        value = (value or "").strip()
        if not value:
            return value
        digits = value.replace("+", "")
        if not digits.isdigit() or len(digits) < 6 or len(digits) > 15 or value.count("+") > 1 or ("+" in value and not value.startswith("+")):
            raise serializers.ValidationError("El telefono debe tener entre 6 y 15 digitos; puede iniciar con +.")
        return value

    def validate_zona_horaria(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("La zona horaria es obligatoria.")
        return value

    def validate_anio_academico_activo(self, value):
        if value and not value.activo:
            raise serializers.ValidationError("El anio academico activo seleccionado esta desactivado.")
        return value

    def validate(self, attrs):
        if self.instance is None and ConfiguracionInstitucional.objects.exists():
            raise serializers.ValidationError("Ya existe una configuracion institucional. Actualice la existente.")
        anio = attrs.get("anio_academico_activo", getattr(self.instance, "anio_academico_activo", None))
        if anio is not None and not AnioAcademico.objects.filter(pk=anio.pk, activo=True).exists():
            raise serializers.ValidationError({"anio_academico_activo": "El anio academico seleccionado no esta activo."})
        return attrs
