from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Curso,
    Docente,
    Estudiante,
    Grado,
    Perfil,
    PeriodoAcademico,
    Seccion,
    VinculoApoderado,
)


User = get_user_model()
ROLE_GROUPS = ("Administrador", "Directivo", "Docente", "Estudiante", "Apoderado")
username_validator = UnicodeUsernameValidator()


class UserMeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    perfil_id = serializers.IntegerField(source="perfil.id", read_only=True)
    estudiante_id = serializers.IntegerField(source="perfil.estudiante.id", read_only=True)
    docente_id = serializers.IntegerField(source="perfil.docente.id", read_only=True)
    apoderado_id = serializers.IntegerField(source="perfil.apoderado.id", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "is_superuser",
            "groups",
            "perfil_id",
            "estudiante_id",
            "docente_id",
            "apoderado_id",
        )
        read_only_fields = fields


class UserAccountSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    dni = serializers.CharField(required=False, allow_blank=True, max_length=20)
    telefono = serializers.CharField(required=False, allow_blank=True, max_length=20)
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=ROLE_GROUPS),
        required=False,
        allow_empty=True,
        write_only=True,
    )
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    perfil_id = serializers.IntegerField(source="perfil.id", read_only=True)
    estudiante_id = serializers.IntegerField(source="perfil.estudiante.id", read_only=True)
    docente_id = serializers.IntegerField(source="perfil.docente.id", read_only=True)
    apoderado_id = serializers.IntegerField(source="perfil.apoderado.id", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "dni",
            "telefono",
            "is_active",
            "is_staff",
            "is_superuser",
            "roles",
            "groups",
            "perfil_id",
            "estudiante_id",
            "docente_id",
            "apoderado_id",
        )
        read_only_fields = (
            "id",
            "full_name",
            "is_staff",
            "is_superuser",
            "groups",
            "perfil_id",
            "estudiante_id",
            "docente_id",
            "apoderado_id",
        )
        extra_kwargs = {
            "username": {"required": True},
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
            "email": {"required": False, "allow_blank": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        perfil = getattr(instance, "perfil", None)
        data["dni"] = perfil.dni if perfil else ""
        data["telefono"] = perfil.telefono if perfil else ""
        return data

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre de usuario es obligatorio.")
        try:
            username_validator(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        queryset = User.objects.filter(username__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un usuario con este nombre de usuario.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if not value:
            return value
        queryset = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")
        return value

    def validate_dni(self, value):
        value = value.strip()
        if not value:
            return value
        if not value.isdigit() or len(value) != 8:
            raise serializers.ValidationError("El DNI debe tener exactamente 8 digitos.")
        queryset = Perfil.objects.filter(dni=value)
        if self.instance is not None and hasattr(self.instance, "perfil"):
            queryset = queryset.exclude(pk=self.instance.perfil.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un perfil con este DNI.")
        return value

    def validate_telefono(self, value):
        value = value.strip()
        if not value:
            return value
        digits = value.replace("+", "")
        if not digits.isdigit() or len(digits) < 6 or len(digits) > 15 or value.count("+") > 1 or ("+" in value and not value.startswith("+")):
            raise serializers.ValidationError("El telefono debe tener entre 6 y 15 digitos; puede iniciar con +.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "La contrasena es obligatoria al crear un usuario."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        dni = validated_data.pop("dni", "")
        telefono = validated_data.pop("telefono", "")
        roles = validated_data.pop("roles", [])
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Perfil.objects.create(user=user, dni=dni, telefono=telefono)
        self._sync_roles(user, roles)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        dni = validated_data.pop("dni", None)
        telefono = validated_data.pop("telefono", None)
        roles = validated_data.pop("roles", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()

        perfil, _ = Perfil.objects.get_or_create(user=instance)
        if dni is not None:
            perfil.dni = dni
        if telefono is not None:
            perfil.telefono = telefono
        perfil.save()

        if roles is not None:
            self._sync_roles(instance, roles)
        return instance

    def _sync_roles(self, user, roles):
        role_groups = [Group.objects.get_or_create(name=role)[0] for role in roles]
        user.groups.remove(*Group.objects.filter(name__in=ROLE_GROUPS))
        if role_groups:
            user.groups.add(*role_groups)
        user.is_staff = user.is_superuser or any(role in {"Administrador", "Directivo"} for role in roles)
        user.save(update_fields=["is_staff"])


class PersonaSerializerMixin(serializers.ModelSerializer):
    role_name = None
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    username = serializers.CharField(write_only=True, required=True, max_length=150)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    first_name = serializers.CharField(write_only=True, required=True, allow_blank=False, max_length=150)
    last_name = serializers.CharField(write_only=True, required=True, allow_blank=False, max_length=150)
    dni = serializers.CharField(write_only=True, required=True, allow_blank=False, max_length=20)
    telefono = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)
    is_active = serializers.BooleanField(write_only=True, required=False, default=True)

    user_id = serializers.IntegerField(source="perfil.user.id", read_only=True)
    perfil_id = serializers.IntegerField(source="perfil.id", read_only=True)
    username_display = serializers.CharField(source="perfil.user.username", read_only=True)
    email_display = serializers.EmailField(source="perfil.user.email", read_only=True)
    first_name_display = serializers.CharField(source="perfil.user.first_name", read_only=True)
    last_name_display = serializers.CharField(source="perfil.user.last_name", read_only=True)
    full_name = serializers.CharField(source="perfil.user.get_full_name", read_only=True)
    dni_display = serializers.CharField(source="perfil.dni", read_only=True)
    telefono_display = serializers.CharField(source="perfil.telefono", read_only=True)
    activo = serializers.BooleanField(source="perfil.user.is_active", read_only=True)
    rol = serializers.SerializerMethodField()

    def get_rol(self, obj) -> str:
        return self.role_name

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre de usuario es obligatorio.")
        try:
            username_validator(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        user = self._get_user_instance()
        queryset = User.objects.filter(username__iexact=value)
        if user is not None:
            queryset = queryset.exclude(pk=user.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un usuario con este nombre de usuario.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if not value:
            return value
        user = self._get_user_instance()
        queryset = User.objects.filter(email__iexact=value)
        if user is not None:
            queryset = queryset.exclude(pk=user.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")
        return value

    def validate_dni(self, value):
        value = value.strip()
        if not value.isdigit() or len(value) != 8:
            raise serializers.ValidationError("El DNI debe tener exactamente 8 digitos.")
        perfil = self._get_perfil_instance()
        queryset = Perfil.objects.filter(dni=value)
        if perfil is not None:
            queryset = queryset.exclude(pk=perfil.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un perfil con este DNI.")
        return value

    def validate_telefono(self, value):
        value = value.strip()
        if not value:
            return value
        digits = value.replace("+", "")
        if not digits.isdigit() or len(digits) < 6 or len(digits) > 15 or value.count("+") > 1 or ("+" in value and not value.startswith("+")):
            raise serializers.ValidationError("El telefono debe tener entre 6 y 15 digitos; puede iniciar con +.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "La contrasena es obligatoria al crear este usuario."})
        return attrs

    def _get_user_instance(self):
        if self.instance is None:
            return None
        return self.instance.perfil.user

    def _get_perfil_instance(self):
        if self.instance is None:
            return None
        return self.instance.perfil

    def _pop_user_data(self, validated_data):
        return {
            "username": validated_data.pop("username", None),
            "password": validated_data.pop("password", None),
            "email": validated_data.pop("email", ""),
            "first_name": validated_data.pop("first_name", None),
            "last_name": validated_data.pop("last_name", None),
            "dni": validated_data.pop("dni", None),
            "telefono": validated_data.pop("telefono", ""),
            "is_active": validated_data.pop("is_active", None),
        }

    def _assign_role(self, user):
        group, _ = Group.objects.get_or_create(name=self.role_name)
        user.groups.add(group)

    def _create_user_and_perfil(self, user_data):
        user = User.objects.create(
            username=user_data["username"],
            email=user_data["email"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            is_active=True if user_data["is_active"] is None else user_data["is_active"],
            is_staff=self.role_name in {"Administrador", "Directivo"},
        )
        user.set_password(user_data["password"])
        user.save()
        self._assign_role(user)
        return Perfil.objects.create(user=user, dni=user_data["dni"], telefono=user_data["telefono"])

    def _update_user_and_perfil(self, instance, user_data):
        user = instance.perfil.user
        perfil = instance.perfil
        for field in ("username", "email", "first_name", "last_name", "is_active"):
            if user_data[field] is not None:
                setattr(user, field, user_data[field])
        if user_data["password"]:
            user.set_password(user_data["password"])
        user.save()
        if user_data["dni"] is not None:
            perfil.dni = user_data["dni"]
        if user_data["telefono"] is not None:
            perfil.telefono = user_data["telefono"]
        perfil.save()
        self._assign_role(user)


class EstudianteSerializer(PersonaSerializerMixin):
    role_name = "Estudiante"
    codigo_estudiante = serializers.CharField(required=True, allow_blank=False, max_length=30)

    class Meta:
        model = Estudiante
        fields = (
            "id",
            "user_id",
            "perfil_id",
            "rol",
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "dni",
            "telefono",
            "is_active",
            "username_display",
            "email_display",
            "first_name_display",
            "last_name_display",
            "full_name",
            "dni_display",
            "telefono_display",
            "activo",
            "codigo_estudiante",
            "fecha_nacimiento",
        )
        read_only_fields = (
            "id",
            "user_id",
            "perfil_id",
            "rol",
            "username_display",
            "email_display",
            "first_name_display",
            "last_name_display",
            "full_name",
            "dni_display",
            "telefono_display",
            "activo",
        )

    def validate_codigo_estudiante(self, value):
        value = value.strip().upper()
        queryset = Estudiante.objects.filter(codigo_estudiante__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un estudiante con este codigo.")
        return value

    def validate_fecha_nacimiento(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("La fecha de nacimiento no puede ser futura.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user_data = self._pop_user_data(validated_data)
        perfil = self._create_user_and_perfil(user_data)
        return Estudiante.objects.create(perfil=perfil, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = self._pop_user_data(validated_data)
        self._update_user_and_perfil(instance, user_data)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class DocenteSerializer(PersonaSerializerMixin):
    role_name = "Docente"

    class Meta:
        model = Docente
        fields = (
            "id",
            "user_id",
            "perfil_id",
            "rol",
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
            "dni",
            "telefono",
            "is_active",
            "username_display",
            "email_display",
            "first_name_display",
            "last_name_display",
            "full_name",
            "dni_display",
            "telefono_display",
            "activo",
        )
        read_only_fields = (
            "id",
            "user_id",
            "perfil_id",
            "rol",
            "username_display",
            "email_display",
            "first_name_display",
            "last_name_display",
            "full_name",
            "dni_display",
            "telefono_display",
            "activo",
        )

    @transaction.atomic
    def create(self, validated_data):
        user_data = self._pop_user_data(validated_data)
        perfil = self._create_user_and_perfil(user_data)
        return Docente.objects.create(perfil=perfil)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = self._pop_user_data(validated_data)
        self._update_user_and_perfil(instance, user_data)
        return instance


class ApoderadoSerializer(PersonaSerializerMixin):
    role_name = "Apoderado"

    class Meta:
        model = Apoderado
        fields = DocenteSerializer.Meta.fields
        read_only_fields = DocenteSerializer.Meta.read_only_fields

    @transaction.atomic
    def create(self, validated_data):
        user_data = self._pop_user_data(validated_data)
        perfil = self._create_user_and_perfil(user_data)
        return Apoderado.objects.create(perfil=perfil)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = self._pop_user_data(validated_data)
        self._update_user_and_perfil(instance, user_data)
        return instance


class VinculoApoderadoSerializer(serializers.ModelSerializer):
    apoderado_label = serializers.StringRelatedField(source="apoderado", read_only=True)
    estudiante_label = serializers.StringRelatedField(source="estudiante", read_only=True)

    class Meta:
        model = VinculoApoderado
        fields = (
            "id",
            "apoderado",
            "apoderado_label",
            "estudiante",
            "estudiante_label",
            "parentesco",
            "es_principal",
        )

    def validate(self, attrs):
        apoderado = attrs.get("apoderado", getattr(self.instance, "apoderado", None))
        estudiante = attrs.get("estudiante", getattr(self.instance, "estudiante", None))
        es_principal = attrs.get("es_principal", getattr(self.instance, "es_principal", False))
        queryset = VinculoApoderado.objects.filter(apoderado=apoderado, estudiante=estudiante)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Este apoderado ya esta vinculado con este estudiante.")
        if es_principal:
            principal_queryset = VinculoApoderado.objects.filter(estudiante=estudiante, es_principal=True)
            if self.instance is not None:
                principal_queryset = principal_queryset.exclude(pk=self.instance.pk)
            if principal_queryset.exists():
                raise serializers.ValidationError({"es_principal": "Este estudiante ya tiene un apoderado principal."})
        return attrs


class AnioAcademicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnioAcademico
        fields = (
            "id",
            "anio",
            "fecha_inicio",
            "fecha_fin",
            "estado",
        )


class PeriodoAcademicoSerializer(serializers.ModelSerializer):
    anio_academico_label = serializers.StringRelatedField(source="anio_academico", read_only=True)

    class Meta:
        model = PeriodoAcademico
        fields = (
            "id",
            "anio_academico",
            "anio_academico_label",
            "nombre",
            "fecha_inicio",
            "fecha_fin",
            "estado",
        )


class GradoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grado
        fields = (
            "id",
            "nombre",
            "nivel",
        )


class SeccionSerializer(serializers.ModelSerializer):
    grado_label = serializers.StringRelatedField(source="grado", read_only=True)

    class Meta:
        model = Seccion
        fields = (
            "id",
            "grado",
            "grado_label",
            "nombre",
        )


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = (
            "id",
            "nombre",
            "descripcion",
            "estado",
        )


class AsignacionCursoSerializer(serializers.ModelSerializer):
    curso_label = serializers.StringRelatedField(source="curso", read_only=True)
    docente_label = serializers.StringRelatedField(source="docente", read_only=True)
    seccion_label = serializers.StringRelatedField(source="seccion", read_only=True)
    anio_academico_label = serializers.StringRelatedField(source="anio_academico", read_only=True)

    class Meta:
        model = AsignacionCurso
        fields = (
            "id",
            "curso",
            "curso_label",
            "docente",
            "docente_label",
            "seccion",
            "seccion_label",
            "anio_academico",
            "anio_academico_label",
            "estado",
        )
