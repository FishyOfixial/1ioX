from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("log_type", models.CharField(choices=[("SIM", "SIM"), ("SUBSCRIPTION", "Subscription"), ("BILLING", "Billing"), ("USER", "User"), ("SYSTEM", "System")], max_length=20)),
                ("severity", models.CharField(choices=[("INFO", "Info"), ("WARNING", "Warning"), ("ERROR", "Error"), ("CRITICAL", "Critical")], default="INFO", max_length=20)),
                ("reference_id", models.CharField(blank=True, max_length=100, null=True)),
                ("message", models.TextField()),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]

