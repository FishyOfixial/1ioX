from datetime import timedelta

from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from auditlogs.models import SystemLog

from ..decorators import matriz_required
from .translations import get_translation


@matriz_required
def administration(request):
    user = request.user
    lang, base = get_translation(user, "dashboard")
    cutoff = timezone.now() - timedelta(days=90)

    # Keep only recent audit logs.
    SystemLog.objects.filter(created_at__lt=cutoff).delete()

    log_type = (request.GET.get("log_type") or "").upper()
    severity = (request.GET.get("severity") or "").upper()
    source = (request.GET.get("source") or "").strip()

    logs_qs = SystemLog.objects.filter(created_at__gte=cutoff).order_by("-created_at")
    if log_type:
        logs_qs = logs_qs.filter(log_type=log_type)
    if severity:
        logs_qs = logs_qs.filter(severity=severity)
    if source:
        logs_qs = logs_qs.filter(metadata__logger_name=source)

    logs_page = Paginator(logs_qs, 50).get_page(request.GET.get("page"))

    context = {
        "base": base,
        "lang": lang,
        "audit_logs": logs_page,
        "selected_log_type": log_type,
        "selected_severity": severity,
        "selected_source": source,
    }
    return render(request, "admin.html", context)

