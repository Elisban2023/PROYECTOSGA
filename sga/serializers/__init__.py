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
    CrearCriterioDocenteSerializer,
    CriterioCalificacionSerializer,
)
from .docente import DocenteCursoSerializer, DocenteEstudianteCursoSerializer
from .asistencia import (
    ActualizarAsistenciaSerializer,
    AsistenciaDocenteSerializer,
    RegistrarAsistenciasSerializer,
)
from .calificaciones import (
    ActualizarCalificacionSerializer,
    CalificacionDocenteSerializer,
    RegistrarCalificacionesSerializer,
)
from .participaciones import (
    ActualizarParticipacionSerializer,
    ParticipacionDocenteSerializer,
    RegistrarParticipacionSerializer,
)
from .observaciones_docente import (
    ActualizarObservacionDocenteSerializer,
    ObservacionDocenteSerializer,
    RegistrarObservacionDocenteSerializer,
)
from .estudiante import EstudianteCursoSerializer
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
    RecomendacionIAPublicacionSerializer,
    RecomendacionIASerializer,
)
from .notificaciones import (
    DestinatarioNotificacionSerializer,
    EnviarNotificacionSerializer,
    NotificacionEstadoSerializer,
    NotificacionSerializer,
)
from .correos import CorreoInstitucionalSerializer, CorreoSolicitudSerializer
from .comunicaciones_docente import ComunicacionDocenteSolicitudSerializer
from .dashboard import DashboardFiltrosSerializer
from .seguimiento_admin import (
    SeguimientoDocenteDetalleSerializer,
    SeguimientoDocenteResumenSerializer,
)

from .auditoria import RegistroAuditoriaSerializer
from .archivos_cloud import (
    BackupBaseDatosSerializer,
    ConfirmarCargaSerializer,
    CrearBackupSerializer,
    JustificacionInasistenciaSerializer,
    RestaurarBackupSerializer,
    RevisarJustificacionSerializer,
    SolicitarCargaJustificacionSerializer,
)
from .configuracion import ConfiguracionInstitucionalSerializer
