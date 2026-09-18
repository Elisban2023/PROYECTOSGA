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
from .seguimiento_admin import seguimiento_docente_admin, seguimiento_docentes_admin
from .acciones_seguimiento import (
    accion_seguimiento_docente_detalle,
    acciones_seguimiento_administracion,
    acciones_seguimiento_apoderado,
    acciones_seguimiento_docente,
    acciones_seguimiento_estudiante,
    actualizar_progreso_apoderado,
    actualizar_progreso_docente,
    actualizar_progreso_estudiante,
)
from .recomendaciones_docente import (
    detalle_recomendacion,
    generar_recomendacion,
    publicar_recomendacion,
    recomendaciones_docente,
    revisar_recomendacion,
)
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
from .notificaciones_usuario import (
    destinatarios_notificacion_docente,
    enviar_notificacion_docente,
    marcar_notificacion_usuario_leida,
    marcar_todas_notificaciones_leidas,
    mis_notificaciones_usuario,
    notificaciones_enviadas_docente,
    resumen_notificaciones_usuario,
)
from .carga_estudiantes import carga_masiva_estudiantes, plantilla_carga_estudiantes
from .carga_apoderados import carga_masiva_apoderados, plantilla_carga_apoderados
from .docente import (
    capacidades_mi_curso,
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
from .correos import CorreoInstitucionalViewSet
from .comunicaciones_docente import (
    comunicaciones_docente,
    detalle_comunicacion_docente,
    enviar_comunicacion,
    previsualizar_comunicacion,
)

from .auditoria import RegistroAuditoriaViewSet
from .configuracion import ConfiguracionInstitucionalViewSet
from .reportes import (
    reporte_academico,
    reporte_incidencias,
    reporte_matriculas,
    reporte_notificaciones,
    reporte_resumen,
)
from .reportes_pdf import exportar_reporte_pdf
from .archivos_cloud import (
    confirmar_carga,
    descargar_justificacion,
    detalle_justificacion_docente,
    justificaciones_administracion,
    justificaciones_apoderado,
    justificaciones_docente,
    justificaciones_estudiante,
    retirar_justificacion,
    revisar_justificacion_docente,
    solicitar_carga,
)
from .backups import (
    backups_administracion,
    crear_backup_administracion,
    detalle_backup_administracion,
    descargar_backup_administracion,
    restaurar_backup_administracion,
)
