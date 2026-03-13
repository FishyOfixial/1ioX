from django.contrib.auth.decorators import login_required
from ..utils import get_assigned_sims
from ..models import Order, SimCard, CommandRunLog, SIMAssignation, Cliente
from billing.models import Subscription
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
import csv
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

    latest_qs = (
        Subscription.objects.filter(sim__iccid__in=assigned_sims)
        .select_related("sim", "plan")
        .order_by("sim_id", "-end_date", "-created_at")
    )

    expired_subscriptions = []
    seen_sim_ids = set()
    for sub in latest_qs:
        if sub.sim_id in seen_sim_ids:
            continue
        seen_sim_ids.add(sub.sim_id)
        if not sub.end_date or sub.end_date >= now:
            continue
        days_expired = max(0, (now - sub.end_date).days)
        if range_days and days_expired < range_days:
            continue
        expired_subscriptions.append({
            "sim_id": sub.sim_id,
            "iccid": sub.sim.iccid,
            "label": sub.sim.label or sub.sim.iccid,
            "plan": sub.plan.name,
            "status": sub.status,
            "end_date": sub.end_date,
            "days_expired": days_expired,
            "last_renewal": sub.start_date,
        })

    sim_ids = [row["sim_id"] for row in expired_subscriptions]
    client_map = {}
    if sim_ids:
        client_ct = ContentType.objects.get_for_model(Cliente)
        for assign in SIMAssignation.objects.filter(sim_id__in=sim_ids, content_type=client_ct):
            if assign.sim_id in client_map:
                continue
            assigned_client = assign.assigned_to
            if isinstance(assigned_client, Cliente):
                client_map[assign.sim_id] = assigned_client

    for row in expired_subscriptions:
        client_obj = client_map.get(row["sim_id"])
        row["client_name"] = f"{client_obj.first_name} {client_obj.last_name}".strip() if client_obj else "-"
        row["client_company"] = client_obj.company or "-" if client_obj else "-"
        row["client_phone"] = client_obj.phone_number or "-" if client_obj else "-"
        row["client_email"] = client_obj.email or "-" if client_obj else "-"

    if (request.GET.get("export_expired") or "").strip() == "1":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=suscripciones_expiradas.csv"
        writer = csv.writer(response)
        writer.writerow([
            "Nombre del cliente asociado",
            "Nombre de la empresa del cliente",
            "Etiqueta de la SIM",
            "Numero de telefono",
            "Correo Electronico",
            "Tiempo expirado (dias)",
            "Ultima renovacion",
        ])
        for row in expired_subscriptions:
            last_renewal = row["last_renewal"].strftime("%Y-%m-%d") if row["last_renewal"] else "-"
            writer.writerow([
                row["client_name"],
                row["client_company"],
                row["label"],
                row["client_phone"],
                row["client_email"],
                row["days_expired"],
                last_renewal,
            ])
        return response

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
