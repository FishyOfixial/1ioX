from django.conf import settings
from django.db import models


class SystemLog(models.Model):
    LOG_TYPES = [
        ("SIM", "SIM"),
        ("SUBSCRIPTION", "Subscription"),
        ("BILLING", "Billing"),
        ("USER", "User"),
        ("SYSTEM", "System"),
    ]

    SEVERITY = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("CRITICAL", "Critical"),
    ]

    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY, default="INFO")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reference_id = models.CharField(max_length=100, null=True, blank=True)
    message = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at} [{self.severity}] {self.log_type}: {self.message[:80]}"

