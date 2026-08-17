from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import filters, mixins, viewsets

from sga.models import RegistroAuditoria
from sga.permissions import IsAdminOrDirectivo
from sga.serializers import RegistroAuditoriaSerializer


class RegistroAuditoriaViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAdminOrDirectivo,)
    serializer_class = RegistroAuditoriaSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "accion",
        "modulo",
        "entidad",
        "entidad_id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )
    ordering_fields = ("fecha", "accion", "modulo", "entidad", "user__username")
    ordering = ("-fecha",)

    def get_queryset(self):
        queryset = RegistroAuditoria.objects.select_related("user").order_by("-fecha")
        filters_map = {
            "user": "user_id",
            "accion": "accion__iexact",
            "modulo": "modulo__iexact",
            "entidad": "entidad__iexact",
            "entidad_id": "entidad_id",
        }
        for param, field in filters_map.items():
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})

        fecha_desde = self._parse_date_param("fecha_desde")
        fecha_hasta = self._parse_date_param("fecha_hasta")
        if fecha_desde:
            queryset = queryset.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha__date__lte=fecha_hasta)
        return queryset

    def _parse_date_param(self, param):
        value = self.request.query_params.get(param)
        if not value:
            return None
        parsed_datetime = parse_datetime(value)
        if parsed_datetime:
            return parsed_datetime.date()
        return parse_date(value)
