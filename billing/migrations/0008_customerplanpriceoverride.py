from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0007_seed_test_plan_1_day"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerPlanPriceOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "adjustment_percent",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="Porcentaje sobre precio base. Ej: -20 = 20% descuento, 15 = 15% recargo.",
                        max_digits=6,
                        validators=[
                            MinValueValidator(Decimal("-100.00")),
                            MaxValueValidator(Decimal("1000.00")),
                        ],
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="customer_price_overrides",
                        to="billing.membershipplan",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="plan_price_overrides",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["user_id", "plan_id"]},
        ),
        migrations.AddConstraint(
            model_name="customerplanpriceoverride",
            constraint=models.UniqueConstraint(
                fields=("user", "plan"),
                name="uq_customer_plan_price_override",
            ),
        ),
    ]
