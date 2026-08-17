from rest_framework import serializers

from sga.models import RegistroAuditoria


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    user_full_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = RegistroAuditoria
        fields = (
            "id",
            "user",
            "user_username",
            "user_full_name",
            "accion",
            "modulo",
            "entidad",
            "entidad_id",
            "fecha",
        )
        read_only_fields = fields
