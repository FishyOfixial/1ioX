from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("SIM_Control", "0006_mercadopago_oauth_fields"),
        ("billing", "0008_customerplanpriceoverride"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionpurchase",
            name="mp_account_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscriptionpurchase",
            name="mp_account_type",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="subscriptionpurchase",
            name="mp_account_user_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.CreateModel(
            name="DistributorSale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("currency", models.CharField(default="MXN", max_length=10)),
                ("payment_id", models.CharField(db_index=True, max_length=100)),
                ("paid_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("approved", "Approved"),
                            ("pending", "Pending"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        max_length=20,
                    ),
                ),
                ("period", models.CharField(db_index=True, max_length=7)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mercado_pago_sales",
                        to="SIM_Control.cliente",
                    ),
                ),
                (
                    "distribuidor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mercado_pago_sales",
                        to="SIM_Control.distribuidor",
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="distributor_sales",
                        to="billing.membershipplan",
                    ),
                ),
                (
                    "purchase",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="distributor_sale",
                        to="billing.subscriptionpurchase",
                    ),
                ),
                (
                    "revendedor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mercado_pago_sales",
                        to="SIM_Control.revendedor",
                    ),
                ),
            ],
            options={
                "ordering": ["-paid_at"],
                "indexes": [
                    models.Index(fields=["distribuidor", "period"], name="billing_dis_distrib_fcd3df_idx"),
                    models.Index(fields=["revendedor", "period"], name="billing_dis_revende_ba08db_idx"),
                ],
            },
        ),
    ]
