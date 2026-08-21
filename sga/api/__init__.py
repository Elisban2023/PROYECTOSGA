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
from .asistencia_estudiante import mi_asistencia
from .calificaciones_estudiante import mis_calificaciones
from .participaciones_estudiante import mi_participacion
from .seguimiento_estudiante import mi_seguimiento
from .apoderado import mis_estudiantes_apoderado
from .asistencia_apoderado import asistencia_apoderado
from .calificaciones_apoderado import calificaciones_apoderado
from .seguimiento_apoderado import seguimiento_apoderado
from .notificaciones_apoderado import marcar_notificacion_leida, mis_notificaciones
from .carga_estudiantes import carga_masiva_estudiantes, plantilla_carga_estudiantes
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
