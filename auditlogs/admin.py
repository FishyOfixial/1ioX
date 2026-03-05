from django.contrib import admin

from .models import SystemLog


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "log_type", "severity", "reference_id", "user")
    list_filter = ("log_type", "severity", "created_at")
    search_fields = ("message", "reference_id", "metadata")
    readonly_fields = ("created_at",)

