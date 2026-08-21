from sga.models import VinculoApoderado


def get_vinculos_apoderado(user):
    apoderado_id = getattr(getattr(getattr(user, "perfil", None), "apoderado", None), "id", None)
    if apoderado_id is None:
        return VinculoApoderado.objects.none()
    return VinculoApoderado.objects.filter(apoderado_id=apoderado_id).select_related(
        "estudiante__perfil__user"
    ).prefetch_related("estudiante__matriculas__seccion__grado", "estudiante__matriculas__anio_academico")
