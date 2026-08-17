from .academico import (
    AnioAcademicoViewSet,
    AsignacionCursoViewSet,
    CursoViewSet,
    GradoViewSet,
    PeriodoAcademicoViewSet,
    SeccionViewSet,
)
from .auth import me, menu
from .matriculas import MatriculaViewSet
from .usuarios import (
    ApoderadoViewSet,
    DocenteViewSet,
    EstudianteViewSet,
    UsuarioViewSet,
    VinculoApoderadoViewSet,
)
from .seguimiento import IncidenciaAcademicaViewSet, ObservacionAcademicaViewSet, RecomendacionIAViewSet
from .notificaciones import NotificacionViewSet
