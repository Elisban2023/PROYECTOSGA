from django.db import migrations, models


ESTADO_ACADEMICO_A_INT = {
    "PLANIFICADO": 1,
    "ACTIVO": 2,
    "CERRADO": 3,
}
ESTADO_ACADEMICO_A_TEXTO = {
    0: "CERRADO",
    1: "PLANIFICADO",
    2: "ACTIVO",
    3: "CERRADO",
}
ESTADO_GENERAL_A_INT = {
    "INACTIVO": 0,
    "ACTIVO": 1,
    "FINALIZADO": 2,
}
ESTADO_GENERAL_A_TEXTO = {
    0: "INACTIVO",
    1: "ACTIVO",
    2: "FINALIZADO",
}


def convertir_estados_a_enteros(apps, schema_editor):
    AnioAcademico = apps.get_model("sga", "AnioAcademico")
    PeriodoAcademico = apps.get_model("sga", "PeriodoAcademico")
    AsignacionCurso = apps.get_model("sga", "AsignacionCurso")

    for anio in AnioAcademico.objects.all().iterator():
        anio.estado_nuevo = (
            ESTADO_ACADEMICO_A_INT.get(anio.estado, 1) if anio.activo else 0
        )
        anio.save(update_fields=["estado_nuevo"])

    for periodo in PeriodoAcademico.objects.all().iterator():
        periodo.estado_nuevo = (
            ESTADO_ACADEMICO_A_INT.get(periodo.estado, 1)
            if periodo.activo
            else 0
        )
        periodo.save(update_fields=["estado_nuevo"])

    for asignacion in AsignacionCurso.objects.all().iterator():
        asignacion.estado_nuevo = ESTADO_GENERAL_A_INT.get(asignacion.estado, 0)
        asignacion.save(update_fields=["estado_nuevo"])


def restaurar_estados_de_texto(apps, schema_editor):
    AnioAcademico = apps.get_model("sga", "AnioAcademico")
    PeriodoAcademico = apps.get_model("sga", "PeriodoAcademico")
    AsignacionCurso = apps.get_model("sga", "AsignacionCurso")

    for anio in AnioAcademico.objects.all().iterator():
        anio.estado = ESTADO_ACADEMICO_A_TEXTO.get(anio.estado_nuevo, "PLANIFICADO")
        anio.activo = anio.estado_nuevo != 0
        anio.save(update_fields=["estado", "activo"])

    for periodo in PeriodoAcademico.objects.all().iterator():
        periodo.estado = ESTADO_ACADEMICO_A_TEXTO.get(
            periodo.estado_nuevo,
            "PLANIFICADO",
        )
        periodo.activo = periodo.estado_nuevo != 0
        periodo.save(update_fields=["estado", "activo"])

    for asignacion in AsignacionCurso.objects.all().iterator():
        asignacion.estado = ESTADO_GENERAL_A_TEXTO.get(
            asignacion.estado_nuevo,
            "INACTIVO",
        )
        asignacion.save(update_fields=["estado"])


class Migration(migrations.Migration):
    dependencies = [
        ("sga", "0006_configuracioninstitucional"),
    ]

    operations = [
        migrations.AddField(
            model_name="anioacademico",
            name="estado_nuevo",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="periodoacademico",
            name="estado_nuevo",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="asignacioncurso",
            name="estado_nuevo",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.RunPython(
            convertir_estados_a_enteros,
            restaurar_estados_de_texto,
        ),
        migrations.RemoveField(
            model_name="anioacademico",
            name="estado",
        ),
        migrations.RemoveField(
            model_name="anioacademico",
            name="activo",
        ),
        migrations.RenameField(
            model_name="anioacademico",
            old_name="estado_nuevo",
            new_name="estado",
        ),
        migrations.AlterField(
            model_name="anioacademico",
            name="estado",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Inactivo"),
                    (1, "Planificado"),
                    (2, "Activo"),
                    (3, "Cerrado"),
                ],
                default=1,
            ),
        ),
        migrations.RemoveField(
            model_name="periodoacademico",
            name="estado",
        ),
        migrations.RemoveField(
            model_name="periodoacademico",
            name="activo",
        ),
        migrations.RenameField(
            model_name="periodoacademico",
            old_name="estado_nuevo",
            new_name="estado",
        ),
        migrations.AlterField(
            model_name="periodoacademico",
            name="estado",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Inactivo"),
                    (1, "Planificado"),
                    (2, "Activo"),
                    (3, "Cerrado"),
                ],
                default=1,
            ),
        ),
        migrations.RenameField(
            model_name="grado",
            old_name="activo",
            new_name="estado",
        ),
        migrations.AlterField(
            model_name="grado",
            name="estado",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Inactivo"), (1, "Activo")],
                default=1,
            ),
        ),
        migrations.RenameField(
            model_name="seccion",
            old_name="activo",
            new_name="estado",
        ),
        migrations.AlterField(
            model_name="seccion",
            name="estado",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Inactivo"), (1, "Activo")],
                default=1,
            ),
        ),
        migrations.AlterField(
            model_name="curso",
            name="estado",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Inactivo"), (1, "Activo")],
                default=1,
            ),
        ),
        migrations.RemoveField(
            model_name="asignacioncurso",
            name="estado",
        ),
        migrations.RenameField(
            model_name="asignacioncurso",
            old_name="estado_nuevo",
            new_name="estado",
        ),
        migrations.AlterField(
            model_name="asignacioncurso",
            name="estado",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Inactivo"),
                    (1, "Activo"),
                    (2, "Finalizado"),
                ],
                default=1,
            ),
        ),
    ]
