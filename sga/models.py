from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone



class EstadoAcademico(models.IntegerChoices):
    INACTIVO = 0, "Inactivo"
    PLANIFICADO = 1, "Planificado"
    ACTIVO = 2, "Activo"
    CERRADO = 3, "Cerrado"


class EstadoGeneral(models.IntegerChoices):
    INACTIVO = 0, "Inactivo"
    ACTIVO = 1, "Activo"
    FINALIZADO = 2, "Finalizado"


class EstadoRegistro(models.IntegerChoices):
    INACTIVO = 0, "Inactivo"
    ACTIVO = 1, "Activo"


class EstadoMatricula(models.TextChoices):
    ACTIVA = "ACTIVA", "Activa"
    RETIRADA = "RETIRADA", "Retirada"
    TRASLADADA = "TRASLADADA", "Trasladada"
    FINALIZADA = "FINALIZADA", "Finalizada"


class EstadoAsistencia(models.TextChoices):
    PRESENTE = "PRESENTE", "Presente"
    TARDE = "TARDE", "Tarde"
    FALTA = "FALTA", "Falta"
    JUSTIFICADA = "JUSTIFICADA", "Justificada"


class NivelLogro(models.TextChoices):
    AD = "AD", "Logro destacado"
    A = "A", "Logro esperado"
    B = "B", "En proceso"
    C = "C", "En inicio"


class Parentesco(models.TextChoices):
    PADRE = "PADRE", "Padre"
    MADRE = "MADRE", "Madre"
    TUTOR = "TUTOR", "Tutor"
    OTRO = "OTRO", "Otro"


class TipoParticipacion(models.TextChoices):
    ORAL = "ORAL", "Oral"
    ESCRITA = "ESCRITA", "Escrita"
    PRACTICA = "PRACTICA", "Practica"
    OTRO = "OTRO", "Otro"


class TipoIncidencia(models.TextChoices):
    ACADEMICA = "ACADEMICA", "Academica"
    CONDUCTUAL = "CONDUCTUAL", "Conductual"
    ASISTENCIA = "ASISTENCIA", "Asistencia"
    OTRO = "OTRO", "Otro"


class NivelIncidencia(models.TextChoices):
    BAJO = "BAJO", "Bajo"
    MEDIO = "MEDIO", "Medio"
    ALTO = "ALTO", "Alto"


class EstadoIncidencia(models.TextChoices):
    ABIERTA = "ABIERTA", "Abierta"
    EN_SEGUIMIENTO = "EN_SEGUIMIENTO", "En seguimiento"
    CERRADA = "CERRADA", "Cerrada"


class EstadoEnvio(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    ENVIADA = "ENVIADA", "Enviada"
    FALLIDA = "FALLIDA", "Fallida"
    LEIDA = "LEIDA", "Leida"


class EstadoRevisionIA(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    APROBADA = "APROBADA", "Aprobada"
    RECHAZADA = "RECHAZADA", "Rechazada"
    EDITADA = "EDITADA", "Editada"

# ============================================================
# USUARIOS Y PERFILES DEL SGA
# ============================================================

class Perfil(models.Model):
    """
    Complementa al usuario de Django con información propia del SGA.
    Relación UML: User 1 --- 1 Perfil.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    dni = models.CharField(max_length=20, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)

    def actualizar_datos(self, **datos):
        """Equivale a actualizarDatos() del UML."""
        campos = {"dni", "telefono"}
        for campo, valor in datos.items():
            if campo in campos:
                setattr(self, campo, valor)
        self.save()

    def __str__(self):
        nombre = self.user.get_full_name().strip()
        return nombre or self.user.get_username()


class Estudiante(models.Model):
    """
    Perfil académico del estudiante.
    Relación UML: Perfil 1 --- 0..1 Estudiante.
    """

    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.CASCADE,
        related_name="estudiante",
    )
    codigo_estudiante = models.CharField(max_length=30, unique=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    def consultar_seguimiento(self):
        """Equivale a consultarSeguimiento() del UML."""
        return {
            "matriculas": self.matriculas.all(),
        }

    def __str__(self):
        return f"{self.codigo_estudiante} - {self.perfil}"


class Docente(models.Model):
    """
    Perfil académico del docente.
    Relación UML: Perfil 1 --- 0..1 Docente.
    """

    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.CASCADE,
        related_name="docente",
    )

    def registrar_asistencia(self, **datos):
        """Equivale a registrarAsistencia() del UML."""
        asignacion = datos.get("asignacion_curso")
        if asignacion is not None and asignacion.docente_id != self.id:
            raise ValidationError(
                "La asignación de curso no pertenece a este docente."
            )
        return Asistencia.objects.create(**datos)

    def registrar_calificacion(self, **datos):
        """Equivale a registrarCalificacion() del UML."""
        asignacion = datos.get("asignacion_curso")
        if asignacion is not None and asignacion.docente_id != self.id:
            raise ValidationError(
                "La asignación de curso no pertenece a este docente."
            )
        return Calificacion.objects.create(**datos)

    def __str__(self):
        return str(self.perfil)


class Apoderado(models.Model):
    """
    Padre, madre o responsable vinculado con uno o más estudiantes.
    Relación UML: Perfil 1 --- 0..1 Apoderado.
    """

    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.CASCADE,
        related_name="apoderado",
    )

    def consultar_avance(self):
        """Equivale a consultarAvance() del UML."""
        estudiantes_ids = self.vinculos_estudiantes.values_list(
            "estudiante_id", flat=True
        )
        return Matricula.objects.filter(
            estudiante_id__in=estudiantes_ids
        ).select_related(
            "estudiante",
            "seccion",
            "anio_academico",
        )

    def __str__(self):
        return str(self.perfil)


class VinculoApoderado(models.Model):
    """
    Clase asociativa entre Apoderado y Estudiante.
    """

    apoderado = models.ForeignKey(
        Apoderado,
        on_delete=models.CASCADE,
        related_name="vinculos_estudiantes",
    )
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name="vinculos_apoderados",
    )
    parentesco = models.CharField(max_length=50, choices=Parentesco.choices)
    es_principal = models.BooleanField(default=False)

    def actualizar_vinculo(self, parentesco=None, es_principal=None):
        """Equivale a actualizarVinculo() del UML."""
        if parentesco is not None:
            self.parentesco = parentesco
        if es_principal is not None:
            self.es_principal = es_principal
        self.save()

    def __str__(self):
        return (
            f"{self.apoderado} - {self.parentesco} - "
            f"{self.estudiante}"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["apoderado", "estudiante"],
                name="unique_vinculo_apoderado_estudiante",
            )
        ]


class RegistroAuditoria(models.Model):
    """
    Auditoría funcional del SGA.
    No reemplaza django_admin_log.
    Relación UML: User 0..1 --- 0..* RegistroAuditoria.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_auditoria_sga",
    )
    accion = models.CharField(max_length=100)
    modulo = models.CharField(max_length=100)
    entidad = models.CharField(max_length=100)
    entidad_id = models.CharField(max_length=100, null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    @classmethod
    def registrar_evento(
        cls,
        *,
        user=None,
        accion,
        modulo,
        entidad,
        entidad_id=None,
    ):
        """Equivale a registrarEvento() del UML."""
        return cls.objects.create(
            user=user,
            accion=accion,
            modulo=modulo,
            entidad=entidad,
            entidad_id=entidad_id,
        )

    def __str__(self):
        usuario = self.user.get_username() if self.user else "Sistema"
        return f"{usuario} - {self.accion} - {self.entidad}"


class ConfiguracionInstitucional(models.Model):
    """Configuracion general visible para la plataforma SGA."""

    nombre_institucion = models.CharField(max_length=200)
    codigo_modular = models.CharField(max_length=30, null=True, blank=True)
    direccion = models.CharField(max_length=250, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    director = models.CharField(max_length=150, null=True, blank=True)
    logo_url = models.URLField(max_length=500, null=True, blank=True)
    zona_horaria = models.CharField(max_length=50, default="America/Lima")
    anio_academico_activo = models.ForeignKey(
        "AnioAcademico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configuraciones_activas",
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre_institucion

    class Meta:
        verbose_name = "Configuracion institucional"
        verbose_name_plural = "Configuraciones institucionales"


# ============================================================
# ESTRUCTURA ACADÉMICA
# ============================================================

class AnioAcademico(models.Model):
    anio = models.PositiveSmallIntegerField(unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.PositiveSmallIntegerField(
        choices=EstadoAcademico.choices,
        default=EstadoAcademico.PLANIFICADO,
    )

    def activar(self):
        """Equivale a activar() del UML."""
        self.estado = EstadoAcademico.ACTIVO
        self.save(update_fields=["estado"])

    def cerrar(self):
        """Equivale a cerrar() del UML."""
        self.estado = EstadoAcademico.CERRADO
        self.save(update_fields=["estado"])

    def __str__(self):
        return str(self.anio)


class PeriodoAcademico(models.Model):
    anio_academico = models.ForeignKey(
        AnioAcademico,
        on_delete=models.PROTECT,
        related_name="periodos",
    )
    nombre = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.PositiveSmallIntegerField(
        choices=EstadoAcademico.choices,
        default=EstadoAcademico.PLANIFICADO,
    )

    def cerrar(self):
        """Equivale a cerrar() del UML."""
        self.estado = EstadoAcademico.CERRADO
        self.save(update_fields=["estado"])

    def __str__(self):
        return f"{self.nombre} - {self.anio_academico}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["anio_academico", "nombre"],
                name="unique_periodo_por_anio",
            )
        ]


class Grado(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.PositiveSmallIntegerField(
        choices=EstadoRegistro.choices,
        default=EstadoRegistro.ACTIVO,
    )

    def actualizar(self, **datos):
        for campo in ("nombre",):
            if campo in datos:
                setattr(self, campo, datos[campo])
        self.save()

    def __str__(self):
        return self.nombre


class Seccion(models.Model):
    grado = models.ForeignKey(
        Grado,
        on_delete=models.PROTECT,
        related_name="secciones",
    )
    nombre = models.CharField(max_length=50)
    estado = models.PositiveSmallIntegerField(
        choices=EstadoRegistro.choices,
        default=EstadoRegistro.ACTIVO,
    )

    def actualizar(self, **datos):
        if "grado" in datos:
            self.grado = datos["grado"]
        if "nombre" in datos:
            self.nombre = datos["nombre"]
        self.save()

    def __str__(self):
        return f"{self.grado.nombre} - {self.nombre}"


class Curso(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    estado = models.PositiveSmallIntegerField(
        choices=EstadoRegistro.choices,
        default=EstadoRegistro.ACTIVO,
    )

    def actualizar(self, **datos):
        for campo in ("nombre", "descripcion"):
            if campo in datos:
                setattr(self, campo, datos[campo])
        self.save()

    def cambiar_estado(self):
        """Equivale a cambiarEstado() del UML."""
        self.estado = (
            EstadoRegistro.INACTIVO
            if self.estado == EstadoRegistro.ACTIVO
            else EstadoRegistro.ACTIVO
        )
        self.save(update_fields=["estado"])

    def __str__(self):
        return self.nombre


# ============================================================
# EVALUACIÓN POR COMPETENCIAS
# ============================================================

class Competencia(models.Model):
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name="competencias",
    )
    nombre = models.CharField(max_length=255)
    estado = models.PositiveSmallIntegerField(
        choices=EstadoRegistro.choices,
        default=EstadoRegistro.ACTIVO,
    )

    def actualizar(self, **datos):
        if "nombre" in datos:
            self.nombre = datos["nombre"]
        if "curso" in datos:
            self.curso = datos["curso"]
        self.save()

    def __str__(self):
        return self.nombre

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["curso", "nombre"],
                name="unique_competencia_por_curso",
            )
        ]


class Capacidad(models.Model):
    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.CASCADE,
        related_name="capacidades",
    )
    nombre = models.CharField(max_length=255)
    estado = models.PositiveSmallIntegerField(
        choices=EstadoRegistro.choices,
        default=EstadoRegistro.ACTIVO,
    )

    def actualizar(self, **datos):
        if "nombre" in datos:
            self.nombre = datos["nombre"]
        if "competencia" in datos:
            self.competencia = datos["competencia"]
        self.save()

    def __str__(self):
        return self.nombre

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["competencia", "nombre"],
                name="unique_capacidad_por_competencia",
            )
        ]


class CriterioCalificacion(models.Model):
    capacidad = models.ForeignKey(
        Capacidad,
        on_delete=models.CASCADE,
        related_name="criterios_calificacion",
    )
    nombre = models.CharField(max_length=255)
    descripcion = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )
    estado = models.PositiveSmallIntegerField(
        choices=EstadoRegistro.choices,
        default=EstadoRegistro.ACTIVO,
    )

    def actualizar(self, **datos):
        for campo in ("nombre", "descripcion"):
            if campo in datos:
                setattr(self, campo, datos[campo])
        if "capacidad" in datos:
            self.capacidad = datos["capacidad"]
        self.save()

    def __str__(self):
        return self.nombre

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["capacidad", "nombre"],
                name="unique_criterio_por_capacidad",
            )
        ]


# ============================================================
# ASIGNACIÓN DE CURSOS Y MATRÍCULA
# ============================================================

class AsignacionCurso(models.Model):
    """
    Une Curso + Docente + Sección + Año académico.
    """

    curso = models.ForeignKey(
        Curso,
        on_delete=models.PROTECT,
        related_name="asignaciones",
    )
    docente = models.ForeignKey(
        Docente,
        on_delete=models.PROTECT,
        related_name="asignaciones_curso",
    )
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.PROTECT,
        related_name="asignaciones_curso",
    )
    anio_academico = models.ForeignKey(
        AnioAcademico,
        on_delete=models.PROTECT,
        related_name="asignaciones_curso",
    )
    estado = models.PositiveSmallIntegerField(
        choices=EstadoGeneral.choices,
        default=EstadoGeneral.ACTIVO,
    )

    def asignar_docente(self, docente):
        """Equivale a asignarDocente() del UML."""
        self.docente = docente
        self.save(update_fields=["docente"])

    def cambiar_estado(self, estado):
        """Equivale a cambiarEstado() del UML."""
        self.estado = estado
        self.save(update_fields=["estado"])

    def __str__(self):
        return (
            f"{self.curso} - {self.seccion} - "
            f"{self.docente} - {self.anio_academico}"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["curso", "seccion", "anio_academico"],
                name="unique_asignacion_curso_seccion_anio",
            )
        ]


class Matricula(models.Model):
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.PROTECT,
        related_name="matriculas",
    )
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.PROTECT,
        related_name="matriculas",
    )
    anio_academico = models.ForeignKey(
        AnioAcademico,
        on_delete=models.PROTECT,
        related_name="matriculas",
    )
    fecha_matricula = models.DateField()
    estado = models.CharField(
        max_length=30,
        choices=EstadoMatricula.choices,
        default=EstadoMatricula.ACTIVA,
    )

    @classmethod
    def registrar(
        cls,
        *,
        estudiante,
        seccion,
        anio_academico,
        fecha_matricula,
        estado,
    ):
        """Equivale a registrar() del UML."""
        return cls.objects.create(
            estudiante=estudiante,
            seccion=seccion,
            anio_academico=anio_academico,
            fecha_matricula=fecha_matricula,
            estado=estado,
        )

    def cambiar_estado(self, estado):
        """Equivale a cambiarEstado() del UML."""
        self.estado = estado
        self.save(update_fields=["estado"])

    def __str__(self):
        return (
            f"{self.estudiante} - {self.seccion} - "
            f"{self.anio_academico}"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["estudiante", "anio_academico"],
                name="unique_matricula_estudiante_anio",
            )
        ]


# ============================================================
# REGISTROS ACADÉMICOS
# ============================================================

class Asistencia(models.Model):
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.PROTECT,
        related_name="asistencias",
    )
    asignacion_curso = models.ForeignKey(
        AsignacionCurso,
        on_delete=models.PROTECT,
        related_name="asistencias",
    )
    fecha = models.DateField()
    estado = models.CharField(
        max_length=30,
        choices=EstadoAsistencia.choices,
    )
    justificacion = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )

    @classmethod
    def registrar(
        cls,
        *,
        matricula,
        asignacion_curso,
        fecha,
        estado,
        justificacion=None,
    ):
        return cls.objects.create(
            matricula=matricula,
            asignacion_curso=asignacion_curso,
            fecha=fecha,
            estado=estado,
            justificacion=justificacion,
        )

    def actualizar(self, **datos):
        for campo in ("fecha", "estado", "justificacion"):
            if campo in datos:
                setattr(self, campo, datos[campo])
        self.save()

    def __str__(self):
        return (
            f"{self.matricula.estudiante} - "
            f"{self.fecha} - {self.estado}"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["matricula", "asignacion_curso", "fecha"],
                name="unique_asistencia_matricula_curso_fecha",
            )
        ]


class Calificacion(models.Model):
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.PROTECT,
        related_name="calificaciones",
    )
    asignacion_curso = models.ForeignKey(
        AsignacionCurso,
        on_delete=models.PROTECT,
        related_name="calificaciones",
    )
    periodo_academico = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        related_name="calificaciones",
    )
    criterio_calificacion = models.ForeignKey(
        CriterioCalificacion,
        on_delete=models.PROTECT,
        related_name="calificaciones",
    )

    # La institución evalúa con niveles de logro AD, A, B y C.
    valor = models.CharField(
        max_length=2,
        choices=NivelLogro.choices,
    )

    observacion = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )

    @classmethod
    def registrar(
        cls,
        *,
        matricula,
        asignacion_curso,
        periodo_academico,
        valor,
        criterio_calificacion,
        observacion=None,
    ):
        return cls.objects.create(
            matricula=matricula,
            asignacion_curso=asignacion_curso,
            periodo_academico=periodo_academico,
            criterio_calificacion=criterio_calificacion,
            valor=valor,
            observacion=observacion,
        )

    def actualizar(self, **datos):
        campos = (
            "periodo_academico",
            "criterio_calificacion",
            "valor",
            "observacion",
        )
        for campo in campos:
            if campo in datos:
                setattr(self, campo, datos[campo])
        self.save()

    def __str__(self):
        return (
            f"{self.matricula.estudiante} - "
            f"{self.asignacion_curso.curso} - {self.valor}"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "matricula",
                    "asignacion_curso",
                    "periodo_academico",
                    "criterio_calificacion",
                ],
                name="unique_calificacion_matricula_curso_periodo_criterio",
            )
        ]


class Participacion(models.Model):
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.PROTECT,
        related_name="participaciones",
    )
    asignacion_curso = models.ForeignKey(
        AsignacionCurso,
        on_delete=models.PROTECT,
        related_name="participaciones",
    )
    periodo_academico = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="participaciones",
    )
    fecha = models.DateTimeField()
    tipo = models.CharField(max_length=100, choices=TipoParticipacion.choices)

    # El UML indica Decimal/String?; se mantiene flexible.
    valor = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )
    observacion = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )

    @classmethod
    def registrar(
        cls,
        *,
        matricula,
        asignacion_curso,
        fecha,
        tipo,
        periodo_academico=None,
        valor=None,
        observacion=None,
    ):
        return cls.objects.create(
            matricula=matricula,
            asignacion_curso=asignacion_curso,
            periodo_academico=periodo_academico,
            fecha=fecha,
            tipo=tipo,
            valor=valor,
            observacion=observacion,
        )

    def __str__(self):
        return (
            f"{self.matricula.estudiante} - "
            f"{self.tipo} - {self.fecha:%Y-%m-%d}"
        )


class ObservacionAcademica(models.Model):
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.PROTECT,
        related_name="observaciones_academicas",
    )
    asignacion_curso = models.ForeignKey(
        AsignacionCurso,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="observaciones_academicas",
    )
    docente = models.ForeignKey(
        Docente,
        on_delete=models.PROTECT,
        related_name="observaciones_registradas",
    )
    fecha = models.DateTimeField()
    categoria = models.CharField(max_length=100)
    descripcion = models.TextField()
    activo = models.BooleanField(default=True)

    @classmethod
    def registrar(
        cls,
        *,
        matricula,
        docente,
        fecha,
        categoria,
        descripcion,
        asignacion_curso=None,
    ):
        return cls.objects.create(
            matricula=matricula,
            asignacion_curso=asignacion_curso,
            docente=docente,
            fecha=fecha,
            categoria=categoria,
            descripcion=descripcion,
        )

    def actualizar(self, **datos):
        campos = (
            "asignacion_curso",
            "docente",
            "fecha",
            "categoria",
            "descripcion",
        )
        for campo in campos:
            if campo in datos:
                setattr(self, campo, datos[campo])
        self.save()

    def __str__(self):
        return (
            f"{self.matricula.estudiante} - "
            f"{self.categoria} - {self.fecha:%Y-%m-%d}"
        )


# ============================================================
# SEGUIMIENTO ESTUDIANTIL
# ============================================================

class IncidenciaAcademica(models.Model):
    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.PROTECT,
        related_name="incidencias_academicas",
    )
    observacion = models.ForeignKey(
        ObservacionAcademica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidencias_generadas",
    )
    tipo = models.CharField(max_length=100, choices=TipoIncidencia.choices)
    descripcion = models.TextField()
    nivel = models.CharField(
        max_length=30,
        choices=NivelIncidencia.choices,
        null=True,
        blank=True,
    )
    estado = models.CharField(
        max_length=30,
        choices=EstadoIncidencia.choices,
        default=EstadoIncidencia.ABIERTA,
    )
    fecha_registro = models.DateTimeField()
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
    )

    @classmethod
    def registrar(
        cls,
        *,
        matricula,
        tipo,
        descripcion,
        estado,
        fecha_registro,
        observacion=None,
        nivel=None,
    ):
        return cls.objects.create(
            matricula=matricula,
            observacion=observacion,
            tipo=tipo,
            descripcion=descripcion,
            nivel=nivel,
            estado=estado,
            fecha_registro=fecha_registro,
        )

    def cerrar(self):
        self.estado = "CERRADA"
        self.fecha_cierre = timezone.now()
        self.save(update_fields=["estado", "fecha_cierre"])

    def __str__(self):
        return (
            f"{self.matricula.estudiante} - "
            f"{self.tipo} - {self.estado}"
        )


class Notificacion(models.Model):
    incidencia = models.ForeignKey(
        IncidenciaAcademica,
        on_delete=models.PROTECT,
        related_name="notificaciones",
    )
    apoderado = models.ForeignKey(
        Apoderado,
        on_delete=models.PROTECT,
        related_name="notificaciones",
    )
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    estado_envio = models.CharField(
        max_length=30,
        choices=EstadoEnvio.choices,
        default=EstadoEnvio.PENDIENTE,
    )
    fecha_envio = models.DateTimeField(
        null=True,
        blank=True,
    )
    fecha_lectura = models.DateTimeField(
        null=True,
        blank=True,
    )
    activo = models.BooleanField(default=True)

    def registrar_envio(self, estado_envio, fecha_envio=None):
        """Equivale a registrarEnvio() del UML."""
        self.estado_envio = estado_envio
        self.fecha_envio = fecha_envio or timezone.now()
        self.save(update_fields=["estado_envio", "fecha_envio"])

    def marcar_como_leida(self):
        """Equivale a marcarComoLeida() del UML."""
        self.fecha_lectura = timezone.now()
        self.save(update_fields=["fecha_lectura"])

    def __str__(self):
        return (
            f"{self.apoderado} - "
            f"{self.titulo} - {self.estado_envio}"
        )


# ============================================================
# RECOMENDACIONES MEDIANTE IA
# ============================================================

class RecomendacionIA(models.Model):
    """
    Conserva la recomendación generada y su revisión humana.
    """

    matricula = models.ForeignKey(
        Matricula,
        on_delete=models.PROTECT,
        related_name="recomendaciones_ia",
    )
    periodo_academico = models.ForeignKey(
        PeriodoAcademico,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recomendaciones_ia",
    )
    revisado_por_docente = models.ForeignKey(
        Docente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recomendaciones_ia_revisadas",
    )
    resumen_contexto = models.TextField()
    texto_generado = models.TextField()
    texto_revisado = models.TextField(
        null=True,
        blank=True,
    )
    estado_revision = models.CharField(
        max_length=30,
        choices=EstadoRevisionIA.choices,
        default=EstadoRevisionIA.PENDIENTE,
    )
    fecha_generacion = models.DateTimeField()
    fecha_revision = models.DateTimeField(
        null=True,
        blank=True,
    )
    activo = models.BooleanField(default=True)

    def registrar_revision(
        self,
        *,
        docente,
        estado_revision,
        texto_revisado=None,
        fecha_revision=None,
    ):
        """Equivale a registrarRevision() del UML."""
        self.revisado_por_docente = docente
        self.estado_revision = estado_revision
        self.texto_revisado = texto_revisado
        self.fecha_revision = fecha_revision or timezone.now()
        self.save(
            update_fields=[
                "revisado_por_docente",
                "estado_revision",
                "texto_revisado",
                "fecha_revision",
            ]
        )

    def actualizar_estado(self, estado_revision):
        """Equivale a actualizarEstado() del UML."""
        self.estado_revision = estado_revision
        self.save(update_fields=["estado_revision"])

    def __str__(self):
        return (
            f"{self.matricula.estudiante} - "
            f"{self.estado_revision} - "
            f"{self.fecha_generacion:%Y-%m-%d}"
        )
