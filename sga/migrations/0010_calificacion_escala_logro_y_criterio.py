from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sga", "0009_remove_grado_nivel"),
    ]

    operations = [
        migrations.AlterField(
            model_name="calificacion",
            name="criterio_calificacion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="calificaciones",
                to="sga.criteriocalificacion",
            ),
        ),
        migrations.AlterField(
            model_name="calificacion",
            name="valor",
            field=models.CharField(
                choices=[
                    ("AD", "Logro destacado"),
                    ("A", "Logro esperado"),
                    ("B", "En proceso"),
                    ("C", "En inicio"),
                ],
                max_length=2,
            ),
        ),
    ]
