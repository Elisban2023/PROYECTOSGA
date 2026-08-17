from .academico import (
    AnioAcademicoViewSet,
    AsignacionCursoViewSet,
    CursoViewSet,
    GradoViewSet,
    PeriodoAcademicoViewSet,
    SeccionViewSet,
)
from .auth import me, menu
from .dashboard import dashboard
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

from .auditoria import RegistroAuditoriaViewSet
from .configuracion import ConfiguracionInstitucionalViewSet
from .reportes import (
    reporte_academico,
    reporte_incidencias,
    reporte_matriculas,
    reporte_notificaciones,
    reporte_resumen,
)
