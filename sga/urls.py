from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import (
    AnioAcademicoViewSet,
    ApoderadoViewSet,
    AsignacionCursoViewSet,
    ConfiguracionInstitucionalViewSet,
    CapacidadViewSet,
    CompetenciaViewSet,
    CriterioCalificacionViewSet,
    CursoViewSet,
    DocenteViewSet,
    EstudianteViewSet,
    GradoViewSet,
    IncidenciaAcademicaViewSet,
    MatriculaViewSet,
    NotificacionViewSet,
    ObservacionAcademicaViewSet,
    PeriodoAcademicoViewSet,
    RecomendacionIAViewSet,
    RegistroAuditoriaViewSet,
    SeccionViewSet,
    UsuarioViewSet,
    VinculoApoderadoViewSet,
    dashboard,
    actualizar_asistencia,
    actualizar_calificacion,
    actualizar_observacion,
    actualizar_participacion,
    asistencias_docente,
    calificaciones_docente,
    criterios_mi_curso,
    estudiantes_mi_curso,
    me,
    menu,
    mis_cursos,
    observaciones_docente,
    periodos_mi_curso,
    participaciones_docente,
    reporte_academico,
    reporte_incidencias,
    reporte_matriculas,
    reporte_notificaciones,
    reporte_resumen,
    registrar_asistencias,
    registrar_calificaciones,
    registrar_observacion,
    registrar_participacion,
    eliminar_observacion,
    detalle_seguimiento_docente,
    seguimiento_docente,
    generar_recomendacion,
    recomendaciones_docente,
    reporte_docente_asistencias,
    reporte_docente_calificaciones,
    reporte_docente_resumen,
    reporte_docente_seguimiento,
)

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("estudiantes", EstudianteViewSet, basename="estudiante")
router.register("docentes", DocenteViewSet, basename="docente")
router.register("apoderados", ApoderadoViewSet, basename="apoderado")
router.register("vinculos-apoderados", VinculoApoderadoViewSet, basename="vinculo-apoderado")
router.register("matriculas", MatriculaViewSet, basename="matricula")
router.register("observaciones", ObservacionAcademicaViewSet, basename="observacion")
router.register("incidencias", IncidenciaAcademicaViewSet, basename="incidencia")
router.register("notificaciones", NotificacionViewSet, basename="notificacion")
router.register("recomendaciones-ia", RecomendacionIAViewSet, basename="recomendacion-ia")
router.register("anios-academicos", AnioAcademicoViewSet, basename="anio-academico")
router.register("periodos", PeriodoAcademicoViewSet, basename="periodo-academico")
router.register("grados", GradoViewSet, basename="grado")
router.register("secciones", SeccionViewSet, basename="seccion")
router.register("cursos", CursoViewSet, basename="curso")
router.register("competencias", CompetenciaViewSet, basename="competencia")
router.register("capacidades", CapacidadViewSet, basename="capacidad")
router.register(
    "criterios-calificacion",
    CriterioCalificacionViewSet,
    basename="criterio-calificacion",
)
router.register("asignaciones-cursos", AsignacionCursoViewSet, basename="asignacion-curso")
router.register("auditoria", RegistroAuditoriaViewSet, basename="auditoria")
router.register("configuracion", ConfiguracionInstitucionalViewSet, basename="configuracion")

urlpatterns = [
    path("auth/me/", me, name="api-auth-me"),
    path("auth/menu/", menu, name="api-auth-menu"),
    path("dashboard/", dashboard, name="api-dashboard"),
    path("docente/mis-cursos/", mis_cursos, name="api-docente-mis-cursos"),
    path(
        "docente/mis-cursos/<int:asignacion_id>/estudiantes/",
        estudiantes_mi_curso,
        name="api-docente-estudiantes-mi-curso",
    ),
    path(
        "docente/mis-cursos/<int:asignacion_id>/periodos/",
        periodos_mi_curso,
        name="api-docente-periodos-mi-curso",
    ),
    path(
        "docente/mis-cursos/<int:asignacion_id>/criterios/",
        criterios_mi_curso,
        name="api-docente-criterios-mi-curso",
    ),
    path(
        "docente/asistencias/",
        asistencias_docente,
        name="api-docente-asistencias",
    ),
    path(
        "docente/asistencias/registrar/",
        registrar_asistencias,
        name="api-docente-registrar-asistencias",
    ),
    path(
        "docente/asistencias/<int:asistencia_id>/",
        actualizar_asistencia,
        name="api-docente-actualizar-asistencia",
    ),
    path(
        "docente/calificaciones/",
        calificaciones_docente,
        name="api-docente-calificaciones",
    ),
    path(
        "docente/calificaciones/registrar/",
        registrar_calificaciones,
        name="api-docente-registrar-calificaciones",
    ),
    path(
        "docente/calificaciones/<int:calificacion_id>/",
        actualizar_calificacion,
        name="api-docente-actualizar-calificacion",
    ),
    path(
        "docente/participaciones/",
        participaciones_docente,
        name="api-docente-participaciones",
    ),
    path(
        "docente/participaciones/registrar/",
        registrar_participacion,
        name="api-docente-registrar-participacion",
    ),
    path(
        "docente/participaciones/<int:participacion_id>/",
        actualizar_participacion,
        name="api-docente-actualizar-participacion",
    ),
    path(
        "docente/observaciones/",
        observaciones_docente,
        name="api-docente-observaciones",
    ),
    path(
        "docente/observaciones/registrar/",
        registrar_observacion,
        name="api-docente-registrar-observacion",
    ),
    path(
        "docente/observaciones/<int:observacion_id>/",
        actualizar_observacion,
        name="api-docente-actualizar-observacion",
    ),
    path(
        "docente/observaciones/<int:observacion_id>/eliminar/",
        eliminar_observacion,
        name="api-docente-eliminar-observacion",
    ),
    path(
        "docente/seguimiento/",
        seguimiento_docente,
        name="api-docente-seguimiento",
    ),
    path(
        "docente/seguimiento/<int:matricula_id>/",
        detalle_seguimiento_docente,
        name="api-docente-detalle-seguimiento",
    ),
    path("docente/recomendaciones-ia/", recomendaciones_docente, name="api-docente-recomendaciones"),
    path("docente/recomendaciones-ia/generar/", generar_recomendacion, name="api-docente-generar-recomendacion"),
    path("docente/reportes/resumen/", reporte_docente_resumen, name="api-docente-reporte-resumen"),
    path("docente/reportes/asistencias/", reporte_docente_asistencias, name="api-docente-reporte-asistencias"),
    path("docente/reportes/calificaciones/", reporte_docente_calificaciones, name="api-docente-reporte-calificaciones"),
    path("docente/reportes/seguimiento/", reporte_docente_seguimiento, name="api-docente-reporte-seguimiento"),
    path("reportes/resumen/", reporte_resumen, name="api-reporte-resumen"),
    path("reportes/matriculas/", reporte_matriculas, name="api-reporte-matriculas"),
    path("reportes/incidencias/", reporte_incidencias, name="api-reporte-incidencias"),
    path("reportes/notificaciones/", reporte_notificaciones, name="api-reporte-notificaciones"),
    path("reportes/academico/", reporte_academico, name="api-reporte-academico"),
    path("", include(router.urls)),
]
