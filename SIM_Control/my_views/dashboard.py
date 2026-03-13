from django.contrib.auth.decorators import login_required
from ..utils import get_assigned_sims
from ..models import Order, SimCard, CommandRunLog
from billing.models import Subscription
from django.utils import timezone
from datetime import timedelta
from ..utils import get_data_monthly_usage, get_top_data_usage_per_month, get_top_sms_usage_per_month
from ..decorators import user_in
from django.shortcuts import render
from .translations import get_translation

@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def dashboard(request):
    user = request.user

    lang, base = get_translation(user, "dashboard")
    all_orders = Order.objects.all()
    assigned_sims = get_assigned_sims(user)
    now = timezone.now()

    all_sims = SimCard.objects.filter(iccid__in=assigned_sims)
    activadas = all_sims.filter(status='Enabled').count()
    desactivadas = all_sims.filter(status='Disabled').count()
    data_suficiente = all_sims.filter(quota_status='More than 20% available').count()
    data_bajo = all_sims.filter(quota_status='Less than 20% available').count()
    data_sin_volumen = all_sims.filter(quota_status='No volume available').count()
    sms_suficiente = all_sims.filter(quota_status_SMS='More than 20% available').count()
    sms_bajo = all_sims.filter(quota_status_SMS='Less than 20% available').count()
    sms_sin_volumen = all_sims.filter(quota_status_SMS='No volume available').count()

    labels, data_usage, sms_usage = get_data_monthly_usage(all_sims)
    top_data_usage = get_top_data_usage_per_month(all_sims)
    top_sms_usage = get_top_sms_usage_per_month(all_sims)
    
    all_commands = CommandRunLog.objects.all()
    monthly_usage_command = all_commands.filter(command_name="actual_usage").first()
    update_orders_command = all_commands.filter(command_name="update_orders").first()
    update_sims_command = all_commands.filter(command_name="update_sims").first()

    expired_ranges = {
        "15d": ("15 dias", 15),
        "1m": ("1 mes", 30),
        "2m": ("2 meses", 60),
        "3m": ("3 meses", 90),
        "6m": ("6 meses", 180),
        "1y": ("1 año", 365),
    }
    selected_range = (request.GET.get("expired_range") or "").strip()
    range_days = expired_ranges.get(selected_range, (None, None))[1]

    expired_qs = (
        Subscription.objects.filter(sim__iccid__in=assigned_sims, end_date__lt=now)
        .select_related("sim", "plan")
        .order_by("sim_id", "-end_date")
    )

    expired_subscriptions = []
    seen_sim_ids = set()
    for sub in expired_qs:
        if sub.sim_id in seen_sim_ids:
            continue
        seen_sim_ids.add(sub.sim_id)
        days_expired = max(0, (now - sub.end_date).days) if sub.end_date else 0
        if range_days and days_expired < range_days:
            continue
        expired_subscriptions.append({
            "label": sub.sim.label or sub.sim.iccid,
            "plan": sub.plan.name,
            "status": sub.status,
            "end_date": sub.end_date,
            "days_expired": days_expired,
        })

    context = {
        'activadas': activadas,
        'desactivadas': desactivadas,
        'data_suficiente': data_suficiente,
        'data_bajo': data_bajo,
        'data_sin_volumen': data_sin_volumen,
        'sms_suficiente': sms_suficiente,
        'sms_bajo': sms_bajo,
        'sms_sin_volumen': sms_sin_volumen,
        'monthly_usage': {
            'labels': labels,
            'data_usage': data_usage,
            'sms_usage': sms_usage,
            'top_data': top_data_usage,
            'top_sms': top_sms_usage,
        },
        'all_comands': {
            'monthly_usage': monthly_usage_command,
            'update_orders': update_orders_command,
            'update_sims': update_sims_command
        },
        'orders': {
            'all_orders': all_orders
        },
        'expired_subscriptions': expired_subscriptions,
        'expired_ranges': expired_ranges,
        'selected_expired_range': selected_range,
        'lang': lang,
        'base': base,

    }

    return render(request, 'dashboard.html', context)
