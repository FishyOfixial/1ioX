from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("SIM_Control", "0002_dedupe_and_add_unique_constraints"),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "logger_name",
                    models.CharField(
                        choices=[
                            ("billing.1nce", "billing.1nce"),
                            ("billing.mercadopago", "billing.mercadopago"),
                        ],
                        db_index=True,
                        max_length=50,
                    ),
                ),
                ("level", models.CharField(db_index=True, max_length=10)),
                ("message", models.TextField()),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="integrationlog",
            index=models.Index(fields=["logger_name", "created_at"], name="SIM_Control_logger__e4f261_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationlog",
            index=models.Index(fields=["level", "created_at"], name="SIM_Control_level_651f3b_idx"),
        ),
    ]
