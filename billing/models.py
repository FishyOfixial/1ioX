from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class MembershipPlan(models.Model):
    name = models.CharField(max_length=60)
    duration_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membership Plan"
        verbose_name_plural = "Membership Plans"
        ordering = ["duration_days"]

    def __str__(self):
        return f"{self.name} ({self.duration_days} días)"


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
            start_value = self.start_date or timezone.now()
            self.start_date = start_value
            self.end_date = start_value + timedelta(days=self.plan.duration_days)
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

    def overwrite_plan(self, new_plan):
        now = timezone.now()
        with transaction.atomic():
            self.plan = new_plan
            self.start_date = now
            self.end_date = now + timedelta(days=new_plan.duration_days)
            self.status = "active"
            self.save(update_fields=["plan", "start_date", "end_date", "status"])
            self._set_sim_status("Enabled")

    def extend(self, plan=None):
        renewal_plan = plan or self.plan
        now = timezone.now()

        with transaction.atomic():
            self.plan = renewal_plan
            if self.end_date and self.end_date > now:
                self.end_date = self.end_date + timedelta(days=renewal_plan.duration_days)
            else:
                self.start_date = now
                self.end_date = now + timedelta(days=renewal_plan.duration_days)
            self.status = "active"
            self.save(update_fields=["plan", "start_date", "end_date", "status"])
            self._set_sim_status("Enabled")

    def suspend(self):
        with transaction.atomic():
            self.status = "suspended"
            self.save(update_fields=["status"])
            self._set_sim_status("Disabled")

    def cancel(self):
        with transaction.atomic():
            self.status = "cancelled"
            self.auto_renew = False
            self.end_date = timezone.now()
            self.save(update_fields=["status", "auto_renew", "end_date"])
            self._set_sim_status("Disabled")

    def expire(self):
        with transaction.atomic():
            self.status = "expired"
            self.save(update_fields=["status"])
            self._set_sim_status("Disabled")

    def __str__(self):
        return f"{self.sim.iccid} - {self.plan.name} ({self.status})"
