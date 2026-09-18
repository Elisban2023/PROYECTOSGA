from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from rest_framework.exceptions import ValidationError

from sga.models import (
    AccionSeguimiento,
    Asistencia,
    Calificacion,
    ConfiguracionInstitucional,
    Matricula,
)
from sga.roles import (
    ROLE_APODERADO,
    ROLE_DOCENTE,
    ROLE_ESTUDIANTE,
    get_primary_role,
    is_admin_or_directivo,
)
from sga.services.apoderado import get_vinculos_apoderado
from sga.services.dashboard import build_dashboard
from sga.services.estudiante import get_matriculas_estudiante
from sga.services.reportes import (
    build_reporte_academico,
    build_reporte_incidencias,
    build_reporte_matriculas,
    build_reporte_notificaciones,
    build_reporte_resumen,
)
from sga.services.reportes_docente import (
    build_reporte_docente_asistencias,
    build_reporte_docente_calificaciones,
    build_reporte_docente_resumen,
    build_reporte_docente_seguimiento,
)


MAX_FILAS_PDF = 1000


def construir_reporte_pdf(user, datos_validados):
    filtros = dict(datos_validados)
    tipo = filtros.pop("tipo", "dashboard")
    titulo, contenido = _contenido_por_rol(user, tipo, filtros)
    return _renderizar_pdf(user, titulo, contenido, filtros), titulo


def _contenido_por_rol(user, tipo, filtros):
    role = get_primary_role(user)
    if tipo == "dashboard":
        filtros_dashboard = {
            key: value
            for key, value in filtros.items()
            if key
            in {
                "anio_academico",
                "periodo_academico",
                "grado",
                "seccion",
                "docente",
                "asignacion_curso",
                "estudiante",
            }
        }
        return "Dashboard de seguimiento academico", build_dashboard(
            user,
            filtros_dashboard,
        )

    if is_admin_or_directivo(user):
        builders = {
            "resumen": ("Resumen institucional", lambda: build_reporte_resumen()),
            "academico": ("Reporte academico", lambda: build_reporte_academico(filtros)),
            "matriculas": ("Reporte de matriculas", lambda: build_reporte_matriculas(filtros)),
            "incidencias": ("Reporte de incidencias", lambda: build_reporte_incidencias(filtros)),
            "notificaciones": (
                "Reporte de notificaciones",
                lambda: build_reporte_notificaciones(filtros),
            ),
        }
        return _ejecutar_builder(tipo, builders, role or "Administracion")

    if role == ROLE_DOCENTE:
        asignacion_id = filtros.get("asignacion_curso")
        builders = {
            "resumen": (
                "Resumen de cursos del docente",
                lambda: build_reporte_docente_resumen(user, asignacion_id),
            ),
            "asistencias": (
                "Reporte de asistencias",
                lambda: build_reporte_docente_asistencias(user, asignacion_id),
            ),
            "calificaciones": (
                "Reporte de calificaciones",
                lambda: build_reporte_docente_calificaciones(user, asignacion_id),
            ),
            "seguimiento": (
                "Reporte de seguimiento estudiantil",
                lambda: build_reporte_docente_seguimiento(user, asignacion_id),
            ),
        }
        return _ejecutar_builder(tipo, builders, role)

    if role in (ROLE_ESTUDIANTE, ROLE_APODERADO):
        if tipo not in ("resumen", "asistencias", "calificaciones", "seguimiento"):
            raise ValidationError(
                {"tipo": f"El reporte {tipo} no esta disponible para el rol {role}."}
            )
        return _contenido_personal(user, role, tipo, filtros)

    raise ValidationError({"tipo": "El usuario no tiene un rol habilitado para reportes."})


def _ejecutar_builder(tipo, builders, role):
    item = builders.get(tipo)
    if item is None:
        raise ValidationError(
            {"tipo": f"El reporte {tipo} no esta disponible para el rol {role}."}
        )
    titulo, builder = item
    return titulo, builder()


def _contenido_personal(user, role, tipo, filtros):
    matriculas = _matriculas_personales(user, role, filtros.get("estudiante"))
    matriculas = _filtrar_matriculas_personales(matriculas, filtros)
    if tipo == "resumen":
        return "Resumen academico personal", build_dashboard(
            user,
            {
                key: value
                for key, value in filtros.items()
                if key in ("anio_academico", "periodo_academico", "estudiante")
            },
        )

    matricula_ids = matriculas.values_list("id", flat=True)
    if tipo == "asistencias":
        queryset = Asistencia.objects.filter(matricula_id__in=matricula_ids)
        queryset = _filtrar_registros_personales(queryset, filtros, usa_fecha=True)
        return "Reporte personal de asistencias", {
            "total": queryset.count(),
            "registros": list(
                queryset.order_by("-fecha").values(
                    "fecha",
                    "estado",
                    "asignacion_curso__curso__nombre",
                    "matricula__estudiante__perfil__user__first_name",
                    "matricula__estudiante__perfil__user__last_name",
                    "justificacion",
                )[:MAX_FILAS_PDF]
            ),
        }
    if tipo == "calificaciones":
        queryset = Calificacion.objects.filter(matricula_id__in=matricula_ids)
        queryset = _filtrar_registros_personales(
            queryset,
            filtros,
            aplicar_estado=False,
        )
        if filtros.get("periodo_academico"):
            queryset = queryset.filter(periodo_academico_id=filtros["periodo_academico"])
        return "Reporte personal de calificaciones", {
            "total": queryset.count(),
            "registros": list(
                queryset.order_by("-periodo_academico__fecha_inicio").values(
                    "asignacion_curso__curso__nombre",
                    "periodo_academico__nombre",
                    "criterio_calificacion__nombre",
                    "valor",
                    "observacion",
                    "matricula__estudiante__perfil__user__first_name",
                    "matricula__estudiante__perfil__user__last_name",
                )[:MAX_FILAS_PDF]
            ),
        }

    acciones = AccionSeguimiento.objects.filter(
        matricula_id__in=matricula_ids,
        activo=True,
    )
    if role == ROLE_ESTUDIANTE:
        acciones = acciones.filter(visible_estudiante=True)
    else:
        acciones = acciones.filter(visible_apoderado=True)
    acciones = _filtrar_registros_personales(acciones, filtros)
    if filtros.get("periodo_academico"):
        acciones = acciones.filter(periodo_academico_id=filtros["periodo_academico"])
    return "Reporte personal de seguimiento", {
        "total": acciones.count(),
        "acciones": list(
            acciones.order_by("estado", "fecha_limite").values(
                "titulo",
                "tipo",
                "responsable",
                "prioridad",
                "estado",
                "fecha_limite",
                "resultado",
                "asignacion_curso__curso__nombre",
                "matricula__estudiante__perfil__user__first_name",
                "matricula__estudiante__perfil__user__last_name",
            )[:MAX_FILAS_PDF]
        ),
    }


def _matriculas_personales(user, role, estudiante_id):
    if role == ROLE_ESTUDIANTE:
        if estudiante_id:
            raise ValidationError(
                {"estudiante": "El estudiante no puede seleccionar otra identidad."}
            )
        return get_matriculas_estudiante(user)
    vinculos = get_vinculos_apoderado(user)
    if estudiante_id:
        vinculos = vinculos.filter(estudiante_id=estudiante_id)
        if not vinculos.exists():
            raise ValidationError(
                {"estudiante": "El estudiante no esta vinculado al apoderado."}
            )
    return Matricula.objects.filter(
        estudiante_id__in=vinculos.values("estudiante_id")
    )


def _filtrar_matriculas_personales(queryset, filtros):
    if filtros.get("anio_academico"):
        queryset = queryset.filter(anio_academico_id=filtros["anio_academico"])
    return queryset


def _filtrar_registros_personales(
    queryset,
    filtros,
    usa_fecha=False,
    aplicar_estado=True,
):
    if filtros.get("asignacion_curso"):
        queryset = queryset.filter(asignacion_curso_id=filtros["asignacion_curso"])
    if aplicar_estado and filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    if usa_fecha and filtros.get("periodo_academico"):
        from sga.models import PeriodoAcademico

        periodo = PeriodoAcademico.objects.filter(
            pk=filtros["periodo_academico"]
        ).first()
        if periodo is None:
            raise ValidationError(
                {"periodo_academico": "El periodo academico no existe."}
            )
        queryset = queryset.filter(fecha__range=(periodo.fecha_inicio, periodo.fecha_fin))
    return queryset


def _renderizar_pdf(user, titulo, contenido, filtros):
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=15 * mm,
        title=titulo,
        author="Sistema de Gestion Academica",
    )
    estilos = getSampleStyleSheet()
    estilos.add(
        ParagraphStyle(
            name="TituloSGA",
            parent=estilos["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#10224E"),
            alignment=TA_LEFT,
            spaceAfter=7 * mm,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="CeldaSGA",
            parent=estilos["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#172033"),
        )
    )
    estilos.add(
        ParagraphStyle(
            name="CabeceraSGA",
            parent=estilos["CeldaSGA"],
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )
    )
    institucion = ConfiguracionInstitucional.objects.filter(activo=True).first()
    nombre_institucion = (
        institucion.nombre_institucion
        if institucion
        else "Sistema de Gestion Academica"
    )
    nombre_usuario = user.get_full_name().strip() or user.username
    historia = [
        Paragraph(nombre_institucion, estilos["Heading3"]),
        Paragraph(titulo, estilos["TituloSGA"]),
        Paragraph(
            f"Generado: {timezone.localtime():%d/%m/%Y %H:%M} | Usuario: {_texto(nombre_usuario)}",
            estilos["BodyText"],
        ),
        Spacer(1, 4 * mm),
    ]
    if filtros:
        historia.extend(
            [
                Paragraph("Filtros aplicados", estilos["Heading2"]),
                _tabla_clave_valor(filtros, estilos),
                Spacer(1, 5 * mm),
            ]
        )
    _agregar_contenido(historia, contenido, estilos)
    documento.build(
        historia,
        onFirstPage=_pie_pagina,
        onLaterPages=_pie_pagina,
    )
    return buffer.getvalue()


def _agregar_contenido(historia, contenido, estilos):
    if not isinstance(contenido, dict):
        historia.append(Paragraph(_texto(contenido), estilos["BodyText"]))
        return
    escalares = {
        key: value
        for key, value in contenido.items()
        if not isinstance(value, (dict, list, tuple))
    }
    if escalares:
        historia.extend([_tabla_clave_valor(escalares, estilos), Spacer(1, 5 * mm)])
    for key, value in contenido.items():
        if key in escalares:
            continue
        historia.append(Paragraph(_etiqueta(key), estilos["Heading2"]))
        if isinstance(value, dict):
            historia.append(_tabla_clave_valor(value, estilos))
        elif isinstance(value, (list, tuple)):
            historia.append(_tabla_lista(value, estilos))
        else:
            historia.append(Paragraph(_texto(value), estilos["BodyText"]))
        historia.append(Spacer(1, 5 * mm))


def _tabla_clave_valor(datos, estilos):
    filas = [
        [
            Paragraph("Indicador", estilos["CabeceraSGA"]),
            Paragraph("Valor", estilos["CabeceraSGA"]),
        ]
    ]
    for key, value in datos.items():
        filas.append(
            [
                Paragraph(_etiqueta(key), estilos["CeldaSGA"]),
                Paragraph(_texto(value), estilos["CeldaSGA"]),
            ]
        )
    return _estilizar_tabla(Table(filas, colWidths=(65 * mm, 180 * mm), repeatRows=1))


def _tabla_lista(items, estilos):
    if not items:
        return Paragraph("Sin registros para los filtros seleccionados.", estilos["BodyText"])
    if not isinstance(items[0], dict):
        filas = [[Paragraph("Valor", estilos["CabeceraSGA"])]] + [
            [Paragraph(_texto(item), estilos["CeldaSGA"])] for item in items[:MAX_FILAS_PDF]
        ]
        return _estilizar_tabla(Table(filas, colWidths=(245 * mm,), repeatRows=1))
    columnas = list(items[0].keys())[:10]
    ancho = 245 * mm / max(len(columnas), 1)
    filas = [
        [Paragraph(_etiqueta(key), estilos["CabeceraSGA"]) for key in columnas]
    ]
    for item in items[:MAX_FILAS_PDF]:
        filas.append(
            [Paragraph(_texto(item.get(key)), estilos["CeldaSGA"]) for key in columnas]
        )
    return _estilizar_tabla(
        Table(filas, colWidths=[ancho] * len(columnas), repeatRows=1)
    )


def _estilizar_tabla(tabla):
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10224E")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D8DEE9")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabla


def _pie_pagina(canvas, documento):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(14 * mm, 9 * mm, "SGA - Documento generado por el sistema")
    canvas.drawRightString(283 * mm, 9 * mm, f"Pagina {documento.page}")
    canvas.restoreState()


def _etiqueta(value):
    return str(value).replace("__", " - ").replace("_", " ").strip().title()


def _texto(value):
    if value is None or value == "":
        return "-"
    if isinstance(value, dict):
        return "; ".join(f"{_etiqueta(k)}: {_texto(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return "; ".join(_texto(item) for item in value)
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
