from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import (
    AnioAcademicoViewSet,
    ApoderadoViewSet,
    AsignacionCursoViewSet,
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
    SeccionViewSet,
    UsuarioViewSet,
    VinculoApoderadoViewSet,
    me,
    menu,
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
router.register("asignaciones-cursos", AsignacionCursoViewSet, basename="asignacion-curso")

urlpatterns = [
    path("auth/me/", me, name="api-auth-me"),
    path("auth/menu/", menu, name="api-auth-menu"),
    path("", include(router.urls)),
]
