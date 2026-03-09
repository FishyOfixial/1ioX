import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from auditlogs.utils import create_log
from billing.services.subscription_dates import calculate_new_end_date, normalize_to_midday


class MembershipPlan(models.Model):
    PERIOD_UNITS = (
        ("day", "Día"),
        ("month", "Mes"),
        ("year", "Año"),
    )

    name = models.CharField(max_length=60)
    duration_days = models.PositiveIntegerField()
    period_unit = models.CharField(max_length=10, choices=PERIOD_UNITS, null=True, blank=True)
    period_count = models.PositiveIntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membership Plan"
        verbose_name_plural = "Membership Plans"
        ordering = ["duration_days"]

    def __str__(self):
        return f"{self.name}"


class CustomerPlanPriceOverride(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="plan_price_overrides",
    )
    plan = models.ForeignKey(
        "billing.MembershipPlan",
        on_delete=models.CASCADE,
        related_name="customer_price_overrides",
    )
    adjustment_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("-100.00")), MaxValueValidator(Decimal("1000.00"))],
        help_text="Porcentaje sobre precio base. Ej: -20 = 20% descuento, 15 = 15% recargo.",
    )
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id", "plan_id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "plan"], name="uq_customer_plan_price_override"),
        ]

    def __str__(self):
        return f"user={self.user_id} plan={self.plan_id} adj={self.adjustment_percent}%"

    def get_effective_price(self) -> Decimal:
        base_price = self.plan.price or Decimal("0")
        multiplier = Decimal("1") + (self.adjustment_percent / Decimal("100"))
        effective = (base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return max(effective, Decimal("0.00"))


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("suspended", "Suspended"),
        ("cancelled", "Cancelled"),
    ]

    sim = models.ForeignKey(
        "SIM_Control.SimCard",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey("billing.MembershipPlan", on_delete=models.PROTECT)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    auto_renew = models.BooleanField(default=False)
    mp_preapproval_id = models.CharField(max_length=100, blank=True, null=True)
    mp_preapproval_status = models.CharField(max_length=50, blank=True, null=True)
    mp_last_event_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        super().clean()

        if self.status in {"pending", "active"} and self.sim_id:
            conflict_exists = (
                Subscription.objects.filter(
                    sim_id=self.sim_id,
                    status__in=["pending", "active"],
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if conflict_exists:
                raise ValidationError("La SIM ya tiene una suscripción activa o pendiente.")

        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValidationError("La fecha de finalización debe ser posterior a la fecha de inicio.")

    def save(self, *args, **kwargs):
        if self._state.adding:
            start_source = self.start_date
            if self.sim_id:
                has_subscription_history = Subscription.objects.filter(sim_id=self.sim_id).exclude(pk=self.pk).exists()
                if not has_subscription_history:
                    sim_activation_date = getattr(self.sim, "activation_date", None)
                    if sim_activation_date:
                        start_source = sim_activation_date

            start_value = normalize_to_midday(start_source or timezone.now())
            self.start_date = start_value
            self.end_date = calculate_new_end_date(start_value, self.plan)
        self.full_clean()
        return super().save(*args, **kwargs)

    def _set_sim_status(self, status):
        if self.sim.status != status:
            self.sim.status = status
            self.sim.save(update_fields=["status"])

    def activate(self):
        with transaction.atomic():
            self.status = "active"
            self.save(update_fields=["status"])
            self._set_sim_status("Enabled")
            create_log(
                log_type="SUBSCRIPTION",
                message="Subscription activated",
                user=None,
                reference_id=str(self.id),
                metadata={"sim_iccid": self.sim.iccid, "plan": self.plan.name},
            )

    def overwrite_plan(self, new_plan):
        start_date = normalize_to_midday(timezone.now())
        with transaction.atomic():
            previous_plan = self.plan.name if self.plan_id else None
            self.plan = new_plan
            self.start_date = start_date
            self.end_date = calculate_new_end_date(start_date, new_plan)
            self.status = "active"
            self.save(update_fields=["plan", "start_date", "end_date", "status"])
            create_log(
                log_type="SUBSCRIPTION",
                message="Subscription plan overwritten",
                reference_id=str(self.id),
                metadata={
                    "sim_iccid": self.sim.iccid,
                    "previous_plan": previous_plan,
                    "new_plan": new_plan.name,
                    "end_date": self.end_date.isoformat() if self.end_date else None,
                },
            )

    def extend(self, plan=None):
        renewal_plan = plan or self.plan
        now = timezone.now()

        with transaction.atomic():
            self.plan = renewal_plan

            if self.end_date and self.end_date > now:
                base_date = self.end_date
            else:
                base_date = now
                self.start_date = normalize_to_midday(now)

            self.end_date = calculate_new_end_date(base_date, renewal_plan)
            self.status = "active"
            self.save(update_fields=["plan", "start_date", "end_date", "status"])
            self._set_sim_status("Enabled")
            create_log(
                log_type="SUBSCRIPTION",
                message="Subscription renewed",
                reference_id=str(self.id),
                metadata={
                    "sim_iccid": self.sim.iccid,
                    "plan": renewal_plan.name,
                    "end_date": self.end_date.isoformat() if self.end_date else None,
                },
            )

    def suspend(self):
        with transaction.atomic():
            self.status = "suspended"
            self.save(update_fields=["status"])
            self._set_sim_status("Disabled")
            create_log(
                log_type="SUBSCRIPTION",
                severity="WARNING",
                message="Subscription suspended",
                reference_id=str(self.id),
                metadata={"sim_iccid": self.sim.iccid},
            )

    def cancel(self):
        with transaction.atomic():
            self.status = "cancelled"
            self.auto_renew = False
            self.end_date = timezone.now()
            self.save(update_fields=["status", "auto_renew", "end_date"])
            self._set_sim_status("Disabled")
            create_log(
                log_type="SUBSCRIPTION",
                severity="WARNING",
                message="Subscription cancelled",
                reference_id=str(self.id),
                metadata={"sim_iccid": self.sim.iccid},
            )

    def expire(self):
        with transaction.atomic():
            self.status = "expired"
            self.save(update_fields=["status"])
            self._set_sim_status("Disabled")
            create_log(
                log_type="SUBSCRIPTION",
                severity="WARNING",
                message="Subscription expired",
                reference_id=str(self.id),
                metadata={"sim_iccid": self.sim.iccid},
            )

    def __str__(self):
        return f"{self.sim.iccid} - {self.plan.name} ({self.status})"


class SubscriptionPurchase(models.Model):
    ACTION_CHOICES = [
        ("assign", "Assign"),
        ("renew", "Renew"),
    ]
    STATUS_CHOICES = [
        ("created", "Created"),
        ("approved", "Approved"),
        ("pending", "Pending"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription_purchases")
    sim = models.ForeignKey("SIM_Control.SimCard", on_delete=models.CASCADE, related_name="subscription_purchases")
    plan = models.ForeignKey("billing.MembershipPlan", on_delete=models.PROTECT, related_name="subscription_purchases")
    subscription = models.ForeignKey(
        "billing.Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchases",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="MXN")
    mp_preference_id = models.CharField(max_length=100, blank=True, null=True)
    mp_payment_id = models.CharField(max_length=100, blank=True, null=True)
    mp_status = models.CharField(max_length=50, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} - {self.sim.iccid} - {self.status}"
