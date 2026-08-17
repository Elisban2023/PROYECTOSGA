from django.contrib import admin

from .models import (
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Asistencia,
    Calificacion,
    Capacidad,
    Competencia,
    ConfiguracionInstitucional,
    CriterioCalificacion,
    Curso,
    Docente,
    Estudiante,
    Grado,
    IncidenciaAcademica,
    Matricula,
    Notificacion,
    ObservacionAcademica,
    Participacion,
    Perfil,
    PeriodoAcademico,
    RecomendacionIA,
    RegistroAuditoria,
    Seccion,
    VinculoApoderado,
)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("user", "dni", "telefono")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "dni",
        "telefono",
    )
    autocomplete_fields = ("user",)


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ("codigo_estudiante", "perfil", "fecha_nacimiento")
    search_fields = (
        "codigo_estudiante",
        "perfil__user__username",
        "perfil__user__first_name",
        "perfil__user__last_name",
        "perfil__dni",
    )
    autocomplete_fields = ("perfil",)


@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ("perfil",)
    search_fields = (
        "perfil__user__username",
        "perfil__user__first_name",
        "perfil__user__last_name",
        "perfil__dni",
    )
    autocomplete_fields = ("perfil",)


@admin.register(Apoderado)
class ApoderadoAdmin(admin.ModelAdmin):
    list_display = ("perfil",)
    search_fields = (
        "perfil__user__username",
        "perfil__user__first_name",
        "perfil__user__last_name",
        "perfil__dni",
    )
    autocomplete_fields = ("perfil",)


@admin.register(VinculoApoderado)
class VinculoApoderadoAdmin(admin.ModelAdmin):
    list_display = ("apoderado", "estudiante", "parentesco", "es_principal")
    list_filter = ("parentesco", "es_principal")
    search_fields = (
        "apoderado__perfil__user__first_name",
        "apoderado__perfil__user__last_name",
        "estudiante__codigo_estudiante",
        "estudiante__perfil__user__first_name",
        "estudiante__perfil__user__last_name",
    )
    autocomplete_fields = ("apoderado", "estudiante")


@admin.register(ConfiguracionInstitucional)
class ConfiguracionInstitucionalAdmin(admin.ModelAdmin):
    list_display = ("nombre_institucion", "codigo_modular", "director", "anio_academico_activo", "activo")
    list_filter = ("activo", "anio_academico_activo")
    search_fields = ("nombre_institucion", "codigo_modular", "director", "email")
    autocomplete_fields = ("anio_academico_activo",)
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "user", "accion", "modulo", "entidad", "entidad_id")
    list_filter = ("modulo", "accion", "fecha")
    search_fields = ("user__username", "accion", "modulo", "entidad", "entidad_id")
    autocomplete_fields = ("user",)
    readonly_fields = ("fecha",)
    date_hierarchy = "fecha"


@admin.register(AnioAcademico)
class AnioAcademicoAdmin(admin.ModelAdmin):
    list_display = ("anio", "fecha_inicio", "fecha_fin", "estado")
    list_filter = ("estado", "anio")
    search_fields = ("anio",)
    ordering = ("-anio",)


@admin.register(PeriodoAcademico)
class PeriodoAcademicoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "anio_academico", "fecha_inicio", "fecha_fin", "estado")
    list_filter = ("estado", "anio_academico")
    search_fields = ("nombre", "anio_academico__anio")
    autocomplete_fields = ("anio_academico",)
    ordering = ("-anio_academico__anio", "fecha_inicio")


@admin.register(Grado)
class GradoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nivel")
    list_filter = ("nivel",)
    search_fields = ("nombre", "nivel")


@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "grado")
    list_filter = ("grado__nivel", "grado")
    search_fields = ("nombre", "grado__nombre", "grado__nivel")
    autocomplete_fields = ("grado",)


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "descripcion")


@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "curso")
    list_filter = ("curso",)
    search_fields = ("nombre", "curso__nombre")
    autocomplete_fields = ("curso",)


@admin.register(Capacidad)
class CapacidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "competencia", "curso")
    list_filter = ("competencia__curso",)
    search_fields = ("nombre", "competencia__nombre", "competencia__curso__nombre")
    autocomplete_fields = ("competencia",)

    @admin.display(description="Curso")
    def curso(self, obj):
        return obj.competencia.curso


@admin.register(CriterioCalificacion)
class CriterioCalificacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "capacidad", "competencia", "curso")
    list_filter = ("capacidad__competencia__curso",)
    search_fields = (
        "nombre",
        "descripcion",
        "capacidad__nombre",
        "capacidad__competencia__nombre",
        "capacidad__competencia__curso__nombre",
    )
    autocomplete_fields = ("capacidad",)

    @admin.display(description="Competencia")
    def competencia(self, obj):
        return obj.capacidad.competencia

    @admin.display(description="Curso")
    def curso(self, obj):
        return obj.capacidad.competencia.curso


@admin.register(AsignacionCurso)
class AsignacionCursoAdmin(admin.ModelAdmin):
    list_display = ("curso", "docente", "seccion", "anio_academico", "estado")
    list_filter = ("estado", "anio_academico", "seccion__grado", "curso")
    search_fields = (
        "curso__nombre",
        "docente__perfil__user__first_name",
        "docente__perfil__user__last_name",
        "seccion__nombre",
        "seccion__grado__nombre",
    )
    autocomplete_fields = ("curso", "docente", "seccion", "anio_academico")


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ("estudiante", "seccion", "anio_academico", "fecha_matricula", "estado")
    list_filter = ("estado", "anio_academico", "seccion__grado", "fecha_matricula")
    search_fields = (
        "estudiante__codigo_estudiante",
        "estudiante__perfil__user__first_name",
        "estudiante__perfil__user__last_name",
        "seccion__nombre",
        "seccion__grado__nombre",
    )
    autocomplete_fields = ("estudiante", "seccion", "anio_academico")
    date_hierarchy = "fecha_matricula"


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ("matricula", "asignacion_curso", "fecha", "estado")
    list_filter = ("estado", "fecha", "asignacion_curso__curso")
    search_fields = (
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "asignacion_curso__curso__nombre",
    )
    autocomplete_fields = ("matricula", "asignacion_curso")
    date_hierarchy = "fecha"


@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = (
        "matricula",
        "asignacion_curso",
        "periodo_academico",
        "criterio_calificacion",
        "valor",
    )
    list_filter = ("periodo_academico", "asignacion_curso__curso")
    search_fields = (
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "asignacion_curso__curso__nombre",
        "valor",
    )
    autocomplete_fields = (
        "matricula",
        "asignacion_curso",
        "periodo_academico",
        "criterio_calificacion",
    )


@admin.register(Participacion)
class ParticipacionAdmin(admin.ModelAdmin):
    list_display = ("matricula", "asignacion_curso", "periodo_academico", "fecha", "tipo", "valor")
    list_filter = ("tipo", "periodo_academico", "fecha")
    search_fields = (
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "asignacion_curso__curso__nombre",
    )
    autocomplete_fields = ("matricula", "asignacion_curso", "periodo_academico")
    date_hierarchy = "fecha"


@admin.register(ObservacionAcademica)
class ObservacionAcademicaAdmin(admin.ModelAdmin):
    list_display = ("matricula", "docente", "asignacion_curso", "fecha", "categoria")
    list_filter = ("categoria", "fecha", "asignacion_curso__curso")
    search_fields = (
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "docente__perfil__user__first_name",
        "docente__perfil__user__last_name",
        "descripcion",
    )
    autocomplete_fields = ("matricula", "asignacion_curso", "docente")
    date_hierarchy = "fecha"


@admin.register(IncidenciaAcademica)
class IncidenciaAcademicaAdmin(admin.ModelAdmin):
    list_display = ("matricula", "tipo", "nivel", "estado", "fecha_registro", "fecha_cierre")
    list_filter = ("tipo", "nivel", "estado", "fecha_registro")
    search_fields = (
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "descripcion",
    )
    autocomplete_fields = ("matricula", "observacion")
    date_hierarchy = "fecha_registro"


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "apoderado", "incidencia", "estado_envio", "fecha_envio", "fecha_lectura")
    list_filter = ("estado_envio", "fecha_envio", "fecha_lectura")
    search_fields = (
        "titulo",
        "mensaje",
        "apoderado__perfil__user__first_name",
        "apoderado__perfil__user__last_name",
    )
    autocomplete_fields = ("incidencia", "apoderado")
    date_hierarchy = "fecha_envio"


@admin.register(RecomendacionIA)
class RecomendacionIAAdmin(admin.ModelAdmin):
    list_display = (
        "matricula",
        "periodo_academico",
        "estado_revision",
        "revisado_por_docente",
        "fecha_generacion",
        "fecha_revision",
    )
    list_filter = ("estado_revision", "periodo_academico", "fecha_generacion")
    search_fields = (
        "matricula__estudiante__codigo_estudiante",
        "matricula__estudiante__perfil__user__first_name",
        "matricula__estudiante__perfil__user__last_name",
        "resumen_contexto",
        "texto_generado",
        "texto_revisado",
    )
    autocomplete_fields = ("matricula", "periodo_academico", "revisado_por_docente")
    date_hierarchy = "fecha_generacion"
