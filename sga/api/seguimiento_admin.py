from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from sga.models import (
    AsignacionCurso,
    Docente,
    EstadoGeneral,
    EstadoIncidencia,
    EstadoRevisionIA,
)
from sga.permissions import IsAdminOrDirectivo
from sga.serializers import (
    SeguimientoDocenteDetalleSerializer,
    SeguimientoDocenteResumenSerializer,
)


PARAMETROS_DOCENTES = [
    OpenApiParameter("search", str, description="Busca por nombre, usuario, correo o DNI."),
    OpenApiParameter("activo", bool, description="Filtra docentes activos o inactivos."),
    OpenApiParameter("page", int, description="Numero de pagina."),
    OpenApiParameter("page_size", int, description="Resultados por pagina, maximo 100."),
    OpenApiParameter(
        "ordering",
        str,
        enum=[
            "nombre",
            "-nombre",
            "incidencias_abiertas",
            "-incidencias_abiertas",
            "recomendaciones_pendientes",
            "-recomendaciones_pendientes",
        ],
    ),
]


class SeguimientoDocentePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _docentes_con_resumen():
    incidencias = "observaciones_registradas__incidencias_generadas"
    recomendaciones = "asignaciones_curso__recomendaciones_ia"
    return Docente.objects.select_related("perfil__user").annotate(
        asignaciones_activas=Count(
            "asignaciones_curso",
            filter=Q(asignaciones_curso__estado=EstadoGeneral.ACTIVO),
            distinct=True,
        ),
        observaciones_total=Count(
            "observaciones_registradas",
            filter=Q(observaciones_registradas__activo=True),
            distinct=True,
        ),
        incidencias_total=Count(incidencias, distinct=True),
        incidencias_abiertas=Count(
            incidencias,
            filter=Q(
                **{
                    f"{incidencias}__estado__in": (
                        EstadoIncidencia.ABIERTA,
                        EstadoIncidencia.EN_SEGUIMIENTO,
                    )
                }
            ),
            distinct=True,
        ),
        recomendaciones_total=Count(
            recomendaciones,
            filter=Q(**{f"{recomendaciones}__activo": True}),
            distinct=True,
        ),
        recomendaciones_pendientes=Count(
            recomendaciones,
            filter=Q(
                **{
                    f"{recomendaciones}__activo": True,
                    f"{recomendaciones}__estado_revision": EstadoRevisionIA.PENDIENTE,
                }
            ),
            distinct=True,
        ),
    )


def _filtrar_docentes(queryset, query_params):
    search = (query_params.get("search") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(perfil__user__first_name__icontains=search)
            | Q(perfil__user__last_name__icontains=search)
            | Q(perfil__user__username__icontains=search)
            | Q(perfil__user__email__icontains=search)
            | Q(perfil__dni__icontains=search)
        )

    activo = query_params.get("activo")
    if activo is not None:
        valores = {"true": True, "1": True, "false": False, "0": False}
        activo_normalizado = valores.get(activo.lower())
        if activo_normalizado is None:
            raise ValidationError({"activo": "Use true, false, 1 o 0."})
        queryset = queryset.filter(perfil__user__is_active=activo_normalizado)

    ordering = query_params.get("ordering", "nombre")
    ordenamientos = {
        "nombre": ("perfil__user__last_name", "perfil__user__first_name"),
        "-nombre": ("-perfil__user__last_name", "-perfil__user__first_name"),
        "incidencias_abiertas": ("incidencias_abiertas", "perfil__user__last_name"),
        "-incidencias_abiertas": ("-incidencias_abiertas", "perfil__user__last_name"),
        "recomendaciones_pendientes": (
            "recomendaciones_pendientes",
            "perfil__user__last_name",
        ),
        "-recomendaciones_pendientes": (
            "-recomendaciones_pendientes",
            "perfil__user__last_name",
        ),
    }
    if ordering not in ordenamientos:
        raise ValidationError({"ordering": "El ordenamiento no es valido."})
    return queryset.order_by(*ordenamientos[ordering], "pk")


@extend_schema(
    parameters=PARAMETROS_DOCENTES,
    responses=SeguimientoDocenteResumenSerializer(many=True),
)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def seguimiento_docentes_admin(request):
    docentes = _filtrar_docentes(_docentes_con_resumen(), request.query_params)
    paginator = SeguimientoDocentePagination()
    pagina = paginator.paginate_queryset(docentes, request)
    serializer = SeguimientoDocenteResumenSerializer(pagina, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(responses=SeguimientoDocenteDetalleSerializer)
@api_view(["GET"])
@permission_classes([IsAdminOrDirectivo])
def seguimiento_docente_admin(request, docente_id):
    asignaciones = AsignacionCurso.objects.select_related(
        "curso",
        "seccion__grado",
        "anio_academico",
    ).order_by("-anio_academico__anio", "seccion__grado__nombre", "curso__nombre")
    docente = get_object_or_404(
        _docentes_con_resumen().prefetch_related(
            Prefetch(
                "asignaciones_curso",
                queryset=asignaciones,
                to_attr="asignaciones_seguimiento",
            )
        ),
        pk=docente_id,
    )
    return Response(SeguimientoDocenteDetalleSerializer(docente).data)
