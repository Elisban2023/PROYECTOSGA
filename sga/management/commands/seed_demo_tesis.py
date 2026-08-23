from datetime import date, datetime, time

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from sga.models import (
    AnioAcademico,
    Apoderado,
    AsignacionCurso,
    Asistencia,
    Calificacion,
    Capacidad,
    Competencia,
    CriterioCalificacion,
    Curso,
    Docente,
    EstadoAcademico,
    EstadoEnvio,
    EstadoGeneral,
    EstadoMatricula,
    EstadoRegistro,
    Estudiante,
    Grado,
    IncidenciaAcademica,
    Matricula,
    Notificacion,
    ObservacionAcademica,
    Participacion,
    Perfil,
    PeriodoAcademico,
    Seccion,
    VinculoApoderado,
)
from sga.roles import ROLE_APODERADO, ROLE_ESTUDIANTE


class Command(BaseCommand):
    help = "Completa datos sinteticos coherentes para la demostracion de tesis."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma que la base de destino es de desarrollo o demostracion.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError(
                "Use --confirm solo en una base de desarrollo o demostracion."
            )
        anio = AnioAcademico.objects.get(anio=2026)
        periodos = self._configurar_periodos(anio)
        seccion_primero = Seccion.objects.get(
            grado__nombre="PRIMER GRADO",
            nombre="A",
        )
        seccion_segundo = Seccion.objects.get(
            grado__nombre="SEGUNDO GRADO",
            nombre="B",
        )
        cursos = self._configurar_cursos()
        asignaciones = self._configurar_asignaciones(
            anio,
            cursos,
            seccion_primero,
            seccion_segundo,
        )
        criterios = {
            curso.id: self._configurar_criterio(curso)
            for curso in cursos.values()
        }
        estudiantes = self._configurar_estudiantes(
            anio,
            seccion_primero,
            seccion_segundo,
        )
        apoderados = self._configurar_apoderados()
        self._configurar_vinculos(estudiantes, apoderados)
        self._configurar_registros(
            estudiantes,
            asignaciones,
            criterios,
            periodos,
        )
        self._configurar_seguimiento(estudiantes, asignaciones, apoderados)

        self.stdout.write(
            self.style.SUCCESS(
                "Datos de tesis listos: "
                f"{len(estudiantes)} estudiantes, "
                f"{len(apoderados)} apoderados demo, "
                f"{len(asignaciones)} asignaciones."
            )
        )

    def _configurar_periodos(self, anio):
        datos = (
            ("Primer Bimestre", date(2026, 3, 2), date(2026, 5, 8)),
            ("Segundo Bimestre", date(2026, 5, 11), date(2026, 7, 24)),
            ("Tercer Bimestre", date(2026, 8, 3), date(2026, 10, 9)),
            ("Cuarto Bimestre", date(2026, 10, 12), date(2026, 12, 18)),
        )
        tercer_periodo = PeriodoAcademico.objects.filter(
            anio_academico=anio,
            nombre="Tercer Bimestre",
        ).first()
        if tercer_periodo is None:
            tercer_periodo = PeriodoAcademico.objects.filter(
                anio_academico=anio,
                nombre="Segundo Bimestre 2026",
            ).first()
            if tercer_periodo is not None:
                tercer_periodo.nombre = "Tercer Bimestre"
                tercer_periodo.save(update_fields=["nombre"])

        periodos = {}
        for nombre, inicio, fin in datos:
            periodo, _ = PeriodoAcademico.objects.update_or_create(
                anio_academico=anio,
                nombre=nombre,
                defaults={
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                    "estado": EstadoAcademico.ACTIVO,
                },
            )
            periodos[nombre] = periodo
        return periodos

    def _configurar_cursos(self):
        cursos = {
            "arte": Curso.objects.filter(nombre="Arte y Cultura").first(),
            "comunicacion": Curso.objects.filter(
                nombre__startswith="Comunicaci"
            ).first(),
            "matematica": Curso.objects.filter(nombre__startswith="Matem").first(),
        }
        cursos["ciencia"], _ = Curso.objects.get_or_create(
            nombre="Ciencia y Tecnología",
            defaults={
                "descripcion": "Desarrolla competencias cientificas y tecnologicas.",
                "estado": EstadoRegistro.ACTIVO,
            },
        )
        if any(curso is None for curso in cursos.values()):
            raise RuntimeError("Faltan los cursos base de Arte, Comunicacion o Matematica.")
        for curso in cursos.values():
            if curso.estado != EstadoRegistro.ACTIVO:
                curso.estado = EstadoRegistro.ACTIVO
                curso.save(update_fields=["estado"])
        return cursos

    def _configurar_asignaciones(self, anio, cursos, primero, segundo):
        docentes = {
            "ana": Docente.objects.get(perfil__user__username="docente.cusco.01"),
            "bruno": Docente.objects.get(perfil__user__username="docente.cusco.02"),
            "carla": Docente.objects.get(perfil__user__username="docente.cusco.03"),
            "lucia": Docente.objects.get(perfil__user__username="docente.prueba.sga"),
            "edwin": Docente.objects.get(perfil__user__username="Carlos"),
        }
        distribucion = (
            (primero, cursos["arte"], docentes["lucia"]),
            (primero, cursos["comunicacion"], docentes["lucia"]),
            (primero, cursos["matematica"], docentes["ana"]),
            (primero, cursos["ciencia"], docentes["edwin"]),
            (segundo, cursos["arte"], docentes["bruno"]),
            (segundo, cursos["comunicacion"], docentes["carla"]),
            (segundo, cursos["matematica"], docentes["ana"]),
            (segundo, cursos["ciencia"], docentes["edwin"]),
        )
        asignaciones = []
        for seccion, curso, docente in distribucion:
            asignacion, _ = AsignacionCurso.objects.update_or_create(
                curso=curso,
                seccion=seccion,
                anio_academico=anio,
                defaults={
                    "docente": docente,
                    "estado": EstadoGeneral.ACTIVO,
                },
            )
            asignaciones.append(asignacion)
        return asignaciones

    def _configurar_criterio(self, curso):
        nombres = {
            "Arte y Cultura": (
                "Crea proyectos desde los lenguajes artisticos",
                "Explora y experimenta los lenguajes del arte",
                "Comunica una propuesta artistica personal",
            ),
            "Ciencia y Tecnología": (
                "Indaga mediante metodos cientificos",
                "Analiza datos y obtiene conclusiones",
                "Sustenta conclusiones con evidencia",
            ),
        }
        if curso.nombre.startswith("Comunicaci"):
            valores = (
                "Escribe diversos tipos de textos",
                "Organiza y desarrolla ideas",
                "Redacta ideas con coherencia y cohesion",
            )
        elif curso.nombre.startswith("Matem"):
            valores = (
                "Resuelve problemas de cantidad",
                "Usa estrategias y procedimientos de estimacion",
                "Resuelve situaciones usando procedimientos adecuados",
            )
        else:
            valores = nombres[curso.nombre]
        competencia, _ = Competencia.objects.get_or_create(
            curso=curso,
            nombre=valores[0],
            defaults={"estado": EstadoRegistro.ACTIVO},
        )
        capacidad, _ = Capacidad.objects.get_or_create(
            competencia=competencia,
            nombre=valores[1],
            defaults={"estado": EstadoRegistro.ACTIVO},
        )
        criterio, _ = CriterioCalificacion.objects.get_or_create(
            capacidad=capacidad,
            nombre=valores[2],
            defaults={
                "descripcion": "Criterio sintetico para demostracion academica.",
                "estado": EstadoRegistro.ACTIVO,
            },
        )
        return criterio

    def _configurar_estudiantes(self, anio, primero, segundo):
        primero_usernames = (
            "alumno.prueba.sga",
            "camila.quillahuaman",
            "diego.condori",
            "valeria.huanca",
            "jose.tito",
            "mariana.apaza",
        )
        nuevos = (
            ("luciana.quispe", "Luciana", "Quispe", "SEC-2026-006", "70200006"),
            ("adrian.mamani", "Adrian", "Mamani", "SEC-2026-007", "70200007"),
            ("ximena.cusi", "Ximena", "Cusi", "SEC-2026-008", "70200008"),
            ("sebastian.huarca", "Sebastian", "Huarca", "SEC-2026-009", "70200009"),
            ("daniela.sucso", "Daniela", "Sucso", "SEC-2026-010", "70200010"),
        )
        estudiantes = {}
        for username in primero_usernames:
            estudiante = Estudiante.objects.get(perfil__user__username=username)
            self._asegurar_rol(estudiante.perfil.user, ROLE_ESTUDIANTE)
            Matricula.objects.update_or_create(
                estudiante=estudiante,
                anio_academico=anio,
                defaults={
                    "seccion": primero,
                    "fecha_matricula": date(2026, 3, 2),
                    "estado": EstadoMatricula.ACTIVA,
                },
            )
            estudiantes[username] = estudiante

        edith = Estudiante.objects.get(perfil__user__username="Edith")
        self._asegurar_rol(edith.perfil.user, ROLE_ESTUDIANTE)
        Matricula.objects.update_or_create(
            estudiante=edith,
            anio_academico=anio,
            defaults={
                "seccion": segundo,
                "fecha_matricula": date(2026, 3, 2),
                "estado": EstadoMatricula.ACTIVA,
            },
        )
        estudiantes["Edith"] = edith

        for username, nombres, apellidos, codigo, dni in nuevos:
            user, creado = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": nombres,
                    "last_name": apellidos,
                    "email": f"{username}@example.com",
                    "is_active": True,
                },
            )
            if creado:
                user.set_password("DemoEstudiante2026!")
                user.save(update_fields=["password"])
            self._asegurar_rol(user, ROLE_ESTUDIANTE)
            perfil, _ = Perfil.objects.get_or_create(
                user=user,
                defaults={"dni": dni, "telefono": f"984{dni[-6:]}"},
            )
            estudiante, _ = Estudiante.objects.get_or_create(
                perfil=perfil,
                defaults={
                    "codigo_estudiante": codigo,
                    "fecha_nacimiento": date(2013, 5, 15),
                },
            )
            Matricula.objects.update_or_create(
                estudiante=estudiante,
                anio_academico=anio,
                defaults={
                    "seccion": segundo,
                    "fecha_matricula": date(2026, 3, 2),
                    "estado": EstadoMatricula.ACTIVA,
                },
            )
            estudiantes[username] = estudiante
        return estudiantes

    def _configurar_apoderados(self):
        datos = (
            ("apoderado.elena.condori", "Elena", "Condori", "80200001"),
            ("apoderado.marta.huanca", "Marta", "Huanca", "80200002"),
            ("apoderado.pedro.tito", "Pedro", "Tito", "80200003"),
            ("apoderado.luz.apaza", "Luz", "Apaza", "80200004"),
            ("apoderado.julia.quillahuaman", "Julia", "Quillahuaman", "80200005"),
        )
        apoderados = {
            "prueba": Apoderado.objects.get(
                perfil__user__username="apoderado.prueba.sga"
            ),
            "existente": Apoderado.objects.get(
                perfil__user__username="apoderado01"
            ),
        }
        for username, nombres, apellidos, dni in datos:
            user, creado = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": nombres,
                    "last_name": apellidos,
                    "email": f"{username}@example.com",
                    "is_active": True,
                },
            )
            if creado:
                user.set_password("DemoApoderado2026!")
                user.save(update_fields=["password"])
            self._asegurar_rol(user, ROLE_APODERADO)
            perfil, _ = Perfil.objects.get_or_create(
                user=user,
                defaults={"dni": dni, "telefono": f"985{dni[-6:]}"},
            )
            apoderado, _ = Apoderado.objects.get_or_create(perfil=perfil)
            apoderados[username] = apoderado
        return apoderados

    def _configurar_vinculos(self, estudiantes, apoderados):
        relaciones = (
            ("alumno.prueba.sga", "prueba", "MADRE"),
            ("Edith", "existente", "PADRE"),
            ("diego.condori", "apoderado.elena.condori", "MADRE"),
            ("luciana.quispe", "apoderado.elena.condori", "MADRE"),
            ("valeria.huanca", "apoderado.marta.huanca", "MADRE"),
            ("adrian.mamani", "apoderado.marta.huanca", "MADRE"),
            ("jose.tito", "apoderado.pedro.tito", "PADRE"),
            ("ximena.cusi", "apoderado.pedro.tito", "PADRE"),
            ("mariana.apaza", "apoderado.luz.apaza", "MADRE"),
            ("sebastian.huarca", "apoderado.luz.apaza", "MADRE"),
            ("camila.quillahuaman", "apoderado.julia.quillahuaman", "MADRE"),
            ("daniela.sucso", "apoderado.julia.quillahuaman", "MADRE"),
        )
        for estudiante_key, apoderado_key, parentesco in relaciones:
            VinculoApoderado.objects.update_or_create(
                estudiante=estudiantes[estudiante_key],
                apoderado=apoderados[apoderado_key],
                defaults={
                    "parentesco": parentesco,
                    "es_principal": True,
                },
            )

    def _configurar_registros(self, estudiantes, asignaciones, criterios, periodos):
        fechas = (
            date(2026, 4, 10),
            date(2026, 6, 12),
            date(2026, 9, 4),
            date(2026, 11, 6),
        )
        periodos_lista = (
            periodos["Primer Bimestre"],
            periodos["Segundo Bimestre"],
            periodos["Tercer Bimestre"],
            periodos["Cuarto Bimestre"],
        )
        matriculas = list(
            Matricula.objects.filter(
                estudiante__in=estudiantes.values(),
                anio_academico__anio=2026,
                estado=EstadoMatricula.ACTIVA,
            ).select_related("seccion")
        )
        asignaciones_por_seccion = {}
        for asignacion in asignaciones:
            asignaciones_por_seccion.setdefault(asignacion.seccion_id, []).append(
                asignacion
            )

        niveles = ("AD", "A", "A", "B", "A", "B", "C")
        for estudiante_index, matricula in enumerate(matriculas):
            for curso_index, asignacion in enumerate(
                asignaciones_por_seccion[matricula.seccion_id]
            ):
                for fecha_index, fecha in enumerate(fechas):
                    marcador = estudiante_index + curso_index + fecha_index
                    if marcador % 13 == 0:
                        estado, justificacion = (
                            "JUSTIFICADA",
                            "Atencion medica comunicada por el apoderado.",
                        )
                    elif marcador % 11 == 0:
                        estado, justificacion = "FALTA", None
                    elif marcador % 7 == 0:
                        estado, justificacion = "TARDE", None
                    else:
                        estado, justificacion = "PRESENTE", None
                    Asistencia.objects.update_or_create(
                        matricula=matricula,
                        asignacion_curso=asignacion,
                        fecha=fecha,
                        defaults={
                            "estado": estado,
                            "justificacion": justificacion,
                        },
                    )

                criterio = criterios[asignacion.curso_id]
                for periodo_index, periodo in enumerate(periodos_lista):
                    valor = niveles[
                        (estudiante_index + curso_index + periodo_index)
                        % len(niveles)
                    ]
                    Calificacion.objects.update_or_create(
                        matricula=matricula,
                        asignacion_curso=asignacion,
                        periodo_academico=periodo,
                        criterio_calificacion=criterio,
                        defaults={
                            "valor": valor,
                            "observacion": (
                                "Evidencia sintetica registrada para la demostracion."
                            ),
                        },
                    )

                fecha_participacion = timezone.make_aware(
                    datetime.combine(
                        date(2026, 9, 18),
                        time(9 + curso_index, 15),
                    )
                )
                Participacion.objects.update_or_create(
                    matricula=matricula,
                    asignacion_curso=asignacion,
                    fecha=fecha_participacion,
                    defaults={
                        "periodo_academico": periodos["Tercer Bimestre"],
                        "tipo": "ORAL" if curso_index % 2 == 0 else "PRACTICA",
                        "valor": "Destacada" if estudiante_index % 3 == 0 else "Adecuada",
                        "observacion": "Participacion sintetica para validacion del sistema.",
                    },
                )

    def _configurar_seguimiento(self, estudiantes, asignaciones, apoderados):
        matriculas = list(
            Matricula.objects.filter(
                estudiante__in=estudiantes.values(),
                anio_academico__anio=2026,
                estado=EstadoMatricula.ACTIVA,
            ).select_related("estudiante__perfil__user")
        )
        asignaciones_por_seccion = {}
        for asignacion in asignaciones:
            asignaciones_por_seccion.setdefault(asignacion.seccion_id, []).append(
                asignacion
            )
        apoderado_por_estudiante = {
            vinculo.estudiante_id: vinculo.apoderado
            for vinculo in VinculoApoderado.objects.filter(
                estudiante__in=estudiantes.values(),
                es_principal=True,
            ).select_related("apoderado")
        }
        for index, matricula in enumerate(matriculas):
            asignacion = asignaciones_por_seccion[matricula.seccion_id][
                index % len(asignaciones_por_seccion[matricula.seccion_id])
            ]
            fecha = timezone.make_aware(
                datetime.combine(date(2026, 9, 25), time(11, 0))
            )
            observacion, _ = ObservacionAcademica.objects.update_or_create(
                matricula=matricula,
                asignacion_curso=asignacion,
                docente=asignacion.docente,
                categoria="Seguimiento academico",
                defaults={
                    "fecha": fecha,
                    "descripcion": (
                        "El estudiante muestra avances y requiere mantener una "
                        "practica constante durante el bimestre."
                    ),
                    "activo": True,
                },
            )
            if index not in (1, 4, 7, 10):
                continue
            incidencia, _ = IncidenciaAcademica.objects.update_or_create(
                matricula=matricula,
                observacion=observacion,
                tipo="ACADEMICA",
                defaults={
                    "descripcion": (
                        "Se recomienda reforzar la organizacion de actividades "
                        "y realizar seguimiento durante el siguiente mes."
                    ),
                    "nivel": "BAJO" if index % 2 == 0 else "MEDIO",
                    "estado": "EN_SEGUIMIENTO",
                    "fecha_registro": fecha,
                },
            )
            apoderado = apoderado_por_estudiante.get(matricula.estudiante_id)
            if apoderado is not None:
                Notificacion.objects.update_or_create(
                    incidencia=incidencia,
                    apoderado=apoderado,
                    defaults={
                        "titulo": "Seguimiento academico disponible",
                        "mensaje": (
                            "Se registro una actualizacion sintetica del seguimiento "
                            "academico. Revise el detalle desde la plataforma."
                        ),
                        "estado_envio": EstadoEnvio.ENVIADA,
                        "fecha_envio": timezone.now(),
                        "activo": True,
                    },
                )

    def _asegurar_rol(self, user, rol):
        grupo, _ = Group.objects.get_or_create(name=rol)
        user.groups.add(grupo)
