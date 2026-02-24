from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0004_membershipplan_period_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionPurchase",
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
                ("reference", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "action",
                    models.CharField(
                        choices=[("assign", "Assign"), ("renew", "Renew")],
                        max_length=20,
                    ),
                ),
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
                        default="created",
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("currency", models.CharField(default="MXN", max_length=10)),
                ("mp_preference_id", models.CharField(blank=True, max_length=100, null=True)),
                ("mp_payment_id", models.CharField(blank=True, max_length=100, null=True)),
                ("mp_status", models.CharField(blank=True, max_length=50, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscription_purchases",
                        to="billing.membershipplan",
                    ),
                ),
                (
                    "sim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription_purchases",
                        to="SIM_Control.simcard",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="purchases",
                        to="billing.subscription",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription_purchases",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
