from .academico import (
    AnioAcademicoSerializer,
    AsignacionCursoSerializer,
    CursoSerializer,
    GradoSerializer,
    PeriodoAcademicoSerializer,
    SeccionSerializer,
)
from .evaluacion import (
    CapacidadSerializer,
    CompetenciaSerializer,
    CriterioCalificacionSerializer,
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
from .seguimiento import (
    IncidenciaAcademicaSerializer,
    ObservacionAcademicaSerializer,
    RecomendacionIARevisionSerializer,
    RecomendacionIASerializer,
)
from .notificaciones import NotificacionEstadoSerializer, NotificacionSerializer

from .auditoria import RegistroAuditoriaSerializer
from .configuracion import ConfiguracionInstitucionalSerializer
