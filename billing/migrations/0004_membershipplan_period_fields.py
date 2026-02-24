from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_subscription"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershipplan",
            name="period_count",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="membershipplan",
            name="period_unit",
            field=models.CharField(
                blank=True,
                choices=[("day", "Día"), ("month", "Mes"), ("year", "Año")],
                max_length=10,
                null=True,
            ),
        ),
    ]