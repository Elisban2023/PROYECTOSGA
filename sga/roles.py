ROLE_ADMIN = "Administrador"
ROLE_DIRECTIVO = "Directivo"
ROLE_DOCENTE = "Docente"
ROLE_ESTUDIANTE = "Estudiante"
ROLE_APODERADO = "Apoderado"

ADMIN_ROLES = {ROLE_ADMIN, ROLE_DIRECTIVO}
ALL_ROLES = (ROLE_ADMIN, ROLE_DIRECTIVO, ROLE_DOCENTE, ROLE_ESTUDIANTE, ROLE_APODERADO)


def get_user_roles(user):
    if not user or not user.is_authenticated:
        return []
    roles = list(user.groups.filter(name__in=ALL_ROLES).values_list("name", flat=True))
    if user.is_superuser and ROLE_ADMIN not in roles:
        roles.insert(0, ROLE_ADMIN)
    elif user.is_staff and not any(role in ADMIN_ROLES for role in roles):
        roles.insert(0, ROLE_DIRECTIVO)
    return roles


def get_primary_role(user):
    roles = get_user_roles(user)
    for role in ALL_ROLES:
        if role in roles:
            return role
    return None


def has_any_role(user, role_names):
    return any(role in set(role_names) for role in get_user_roles(user))


def is_admin_or_directivo(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.is_staff or has_any_role(user, ADMIN_ROLES)))


def get_user_profile_ids(user):
    perfil = getattr(user, "perfil", None)
    if perfil is None:
        return {"perfil_id": None, "estudiante_id": None, "docente_id": None, "apoderado_id": None}
    return {
        "perfil_id": perfil.id,
        "estudiante_id": getattr(getattr(perfil, "estudiante", None), "id", None),
        "docente_id": getattr(getattr(perfil, "docente", None), "id", None),
        "apoderado_id": getattr(getattr(perfil, "apoderado", None), "id", None),
    }
