from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sga", "0010_calificacion_escala_logro_y_criterio"),
    ]

    operations = [
        migrations.AddField(
            model_name="recomendacionia",
            name="asignacion_curso",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="recomendaciones_ia",
                to="sga.asignacioncurso",
            ),
        ),
    ]
