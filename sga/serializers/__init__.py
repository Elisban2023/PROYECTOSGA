from .academico import (
    AnioAcademicoSerializer,
    AsignacionCursoSerializer,
    CursoSerializer,
    GradoSerializer,
    PeriodoAcademicoSerializer,
    SeccionSerializer,
)
from .matriculas import MatriculaSerializer
from .usuarios import (
    ApoderadoSerializer,
    DocenteSerializer,
    EstudianteSerializer,
    UserAccountSerializer,
    UserMeSerializer,
    VinculoApoderadoSerializer,
)
from .seguimiento import IncidenciaAcademicaSerializer, ObservacionAcademicaSerializer
from .notificaciones import NotificacionEstadoSerializer, NotificacionSerializer
