from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone

from auditlogs.models import SystemLog
from auditlogs.utils import create_log
from billing.models import CustomerPlanPriceOverride, MembershipPlan

from ..decorators import matriz_required
from .translations import get_translation


@matriz_required
def administration(request):
    user = request.user
    lang, base = get_translation(user, "dashboard")
    cutoff = timezone.now() - timedelta(days=90)
    User = get_user_model()

    if request.method == "POST":
        action = (request.POST.get("pricing_action") or "").strip()
        if action == "upsert":
            customer_id = (request.POST.get("customer_id") or "").strip()
            plan_id = (request.POST.get("plan_id") or "").strip()
            adjustment_raw = (request.POST.get("adjustment_percent") or "").strip()
            note = (request.POST.get("note") or "").strip()

            try:
                customer = User.objects.get(id=customer_id, user_type="CLIENTE")
                plan = MembershipPlan.objects.get(id=plan_id)
                adjustment = Decimal(adjustment_raw)
                if adjustment < Decimal("-100"):
                    raise ValueError("adjustment below -100")
            except (User.DoesNotExist, MembershipPlan.DoesNotExist, InvalidOperation, ValueError):
                messages.error(request, "No se pudo guardar: datos invalidos.")
                return redirect("admin")

            override, _ = CustomerPlanPriceOverride.objects.update_or_create(
                user=customer,
                plan=plan,
                defaults={
                    "adjustment_percent": adjustment,
                    "note": note,
                    "is_active": True,
                },
            )
            create_log(
                log_type="BILLING",
                message="Customer plan price override updated from administration",
                user=request.user,
                reference_id=str(override.id),
                metadata={
                    "customer_id": customer.id,
                    "plan_id": plan.id,
                    "adjustment_percent": str(override.adjustment_percent),
                },
            )
            messages.success(request, "Precio personalizado guardado.")
            return redirect("admin")

        if action == "delete":
            override_id = (request.POST.get("override_id") or "").strip()
            override = CustomerPlanPriceOverride.objects.filter(id=override_id).select_related("user", "plan").first()
            if not override:
                messages.error(request, "Override no encontrado.")
                return redirect("admin")
            create_log(
                log_type="BILLING",
                severity="WARNING",
                message="Customer plan price override deleted from administration",
                user=request.user,
                reference_id=str(override.id),
                metadata={
                    "customer_id": override.user_id,
                    "plan_id": override.plan_id,
                    "adjustment_percent": str(override.adjustment_percent),
                },
            )
            override.delete()
            messages.success(request, "Precio personalizado eliminado.")
            return redirect("admin")

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
    customer_options = (
        User.objects.filter(user_type="CLIENTE", is_active=True)
        .order_by("first_name", "last_name", "id")
        .only("id", "first_name", "last_name", "username")
    )
    plan_options = MembershipPlan.objects.filter(is_active=True).order_by("duration_days", "name")
    price_overrides = list(
        CustomerPlanPriceOverride.objects.select_related("user", "plan")
        .order_by("user__id", "plan__duration_days", "plan__name")
    )
    for row in price_overrides:
        row.effective_price = row.get_effective_price()

    context = {
        "base": base,
        "lang": lang,
        "audit_logs": logs_page,
        "selected_log_type": log_type,
        "selected_severity": severity,
        "selected_source": source,
        "customer_options": customer_options,
        "plan_options": plan_options,
        "price_overrides": price_overrides,
    }
    return render(request, "admin.html", context)
