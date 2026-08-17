from sga.roles import ROLE_APODERADO, ROLE_DOCENTE, ROLE_ESTUDIANTE, get_primary_role, get_user_roles, is_admin_or_directivo


ADMIN_MENU = [
    {"label": "Dashboard", "path": "/dashboard"},
    {
        "label": "Gestion academica",
        "children": [
            {"label": "Anios academicos", "path": "/gestion-academica/anios-academicos"},
            {"label": "Periodos", "path": "/gestion-academica/periodos"},
            {"label": "Grados y secciones", "path": "/gestion-academica/grados-secciones"},
            {"label": "Cursos", "path": "/gestion-academica/cursos"},
            {"label": "Asignacion de cursos", "path": "/gestion-academica/asignaciones-cursos"},
        ],
    },
    {
        "label": "Usuarios",
        "children": [
            {"label": "Estudiantes", "path": "/usuarios/estudiantes"},
            {"label": "Docentes", "path": "/usuarios/docentes"},
            {"label": "Apoderados", "path": "/usuarios/apoderados"},
            {"label": "Usuarios y roles", "path": "/usuarios/roles"},
        ],
    },
    {"label": "Matriculas", "path": "/matriculas"},
    {
        "label": "Seguimiento",
        "children": [
            {"label": "Incidencias", "path": "/seguimiento/incidencias"},
            {"label": "Observaciones", "path": "/seguimiento/observaciones"},
            {"label": "Recomendaciones IA", "path": "/seguimiento/recomendaciones-ia"},
        ],
    },
    {"label": "Reportes", "path": "/reportes"},
    {"label": "Auditoria", "path": "/auditoria"},
    {"label": "Configuracion", "path": "/configuracion"},
]

ROLE_MENUS = {
    ROLE_DOCENTE: [
        {"label": "Dashboard", "path": "/dashboard"},
        {"label": "Mis cursos", "path": "/docente/mis-cursos"},
        {"label": "Asistencia", "path": "/docente/asistencia"},
        {"label": "Calificaciones", "path": "/docente/calificaciones"},
        {"label": "Participaciones", "path": "/docente/participaciones"},
        {"label": "Observaciones", "path": "/docente/observaciones"},
        {"label": "Seguimiento estudiantil", "path": "/docente/seguimiento"},
        {"label": "Recomendaciones IA", "path": "/docente/recomendaciones-ia"},
        {"label": "Reportes", "path": "/docente/reportes"},
    ],
    ROLE_ESTUDIANTE: [
        {"label": "Dashboard", "path": "/dashboard"},
        {"label": "Mis cursos", "path": "/estudiante/mis-cursos"},
        {"label": "Mi asistencia", "path": "/estudiante/mi-asistencia"},
        {"label": "Mis calificaciones", "path": "/estudiante/mis-calificaciones"},
        {"label": "Mi participacion", "path": "/estudiante/mi-participacion"},
        {"label": "Mi seguimiento", "path": "/estudiante/mi-seguimiento"},
    ],
    ROLE_APODERADO: [
        {"label": "Dashboard", "path": "/dashboard"},
        {"label": "Mis estudiantes", "path": "/apoderado/mis-estudiantes"},
        {"label": "Asistencia", "path": "/apoderado/asistencia"},
        {"label": "Calificaciones", "path": "/apoderado/calificaciones"},
        {"label": "Seguimiento", "path": "/apoderado/seguimiento"},
        {"label": "Notificaciones", "path": "/apoderado/notificaciones"},
    ],
}


def build_menu(user):
    roles = get_user_roles(user)
    primary_role = get_primary_role(user)
    if is_admin_or_directivo(user):
        items = ADMIN_MENU
    else:
        items = ROLE_MENUS.get(primary_role, [{"label": "Dashboard", "path": "/dashboard"}])
    return {"role": primary_role, "roles": roles, "items": items}
