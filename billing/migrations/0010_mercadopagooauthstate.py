from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("billing", "0009_mercadopago_connected_sales"),
    ]

    operations = [
        migrations.CreateModel(
            name="MercadoPagoOAuthState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("state", models.CharField(max_length=128, unique=True)),
                (
                    "profile_type",
                    models.CharField(
                        choices=[("distribuidor", "Distribuidor"), ("revendedor", "Revendedor")],
                        max_length=20,
                    ),
                ),
                ("profile_id", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mercado_pago_oauth_states",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["state", "used_at"], name="billing_mer_state_95c674_idx"),
                    models.Index(fields=["user", "created_at"], name="billing_mer_user_id_71adb4_idx"),
                ],
            },
        ),
    ]
