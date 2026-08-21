from .academico import (
    AnioAcademicoViewSet,
    AsignacionCursoViewSet,
    CursoViewSet,
    GradoViewSet,
    PeriodoAcademicoViewSet,
    SeccionViewSet,
)
from .evaluacion import (
    CapacidadViewSet,
    CompetenciaViewSet,
    CriterioCalificacionViewSet,
)
from .auth import me, menu
from .asistencia import (
    actualizar_asistencia,
    asistencias_docente,
    registrar_asistencias,
)
from .calificaciones import (
    actualizar_calificacion,
    calificaciones_docente,
    registrar_calificaciones,
)
from .participaciones import (
    actualizar_participacion,
    participaciones_docente,
    registrar_participacion,
)
from .observaciones_docente import (
    actualizar_observacion,
    eliminar_observacion,
    observaciones_docente,
    registrar_observacion,
)
from .seguimiento_docente import detalle_seguimiento_docente, seguimiento_docente
from .recomendaciones_docente import generar_recomendacion, recomendaciones_docente
from .reportes_docente import (
    reporte_docente_asistencias,
    reporte_docente_calificaciones,
    reporte_docente_resumen,
    reporte_docente_seguimiento,
)
from .estudiante import mis_cursos_estudiante
from .docente import (
    criterios_mi_curso,
    estudiantes_mi_curso,
    mis_cursos,
    periodos_mi_curso,
)
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
