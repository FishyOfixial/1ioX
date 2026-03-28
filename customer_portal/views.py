import json
import hmac

from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from auditlogs.utils import create_log
from billing.models import MembershipPlan, SubscriptionPurchase
from billing.pricing import attach_effective_prices_for_user, resolve_plan_price_for_user
from SIM_Control.models import Vehicle, SIMAssignation, Cliente
from SIM_Control.security import get_client_ip, get_public_base_url
from customer_portal.decorators import customer_required
from customer_portal.services.payments_service import (
    create_checkout_for_bulk_plan,
    create_checkout_for_plan,
    create_auto_renew_checkout_for_subscription,
    disable_subscription_auto_renew,
    process_mercadopago_preapproval,
    process_mercadopago_payment,
)
from customer_portal.services.sim_service import get_client_sims
from customer_portal.translations import LANG_PORTAL


def _is_prepago_plan(plan: MembershipPlan | None) -> bool:
    if not plan:
        return False
    return plan.duration_days == 1825


def _get_valid_bulk_selection(request, lang):
    sims_qs = get_client_sims(request.user)
    selected_ids = request.POST.getlist("sim_ids")
    if not selected_ids:
        messages.error(request, lang["bulk_no_sims_selected"])
        return None, None

    try:
        selected_ids = [int(sim_id) for sim_id in selected_ids]
    except (TypeError, ValueError):
        messages.error(request, lang["bulk_invalid_selection"])
        return None, None

    sims = list(sims_qs.filter(id__in=selected_ids))
    if not sims or len(sims) != len(set(selected_ids)):
        messages.error(request, lang["bulk_invalid_selection"])
        return None, None

    plan_id = request.POST.get("plan_id")
    if not plan_id:
        messages.error(request, lang["bulk_select_plan"])
        return None, None

    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    if _is_prepago_plan(plan):
        messages.error(request, lang["prepay_not_available"])
        return None, None

    return sims, plan


def _get_payment_callback_urls(request):
    base_url = get_public_base_url(request)
    notification_url = f"{base_url}{reverse('mercadopago_webhook_root')}"
    return base_url, notification_url


@customer_required
def customer_dashboard(request):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims = get_client_sims(request.user)
    query = (request.GET.get("q") or "").strip()
    selected_sub_status = (request.GET.get("sub_status") or "").strip()

    if query:
        sims = sims.filter(iccid__icontains=query)

    membership_plans = (
        MembershipPlan.objects.filter(is_active=True)
        .exclude(duration_days__in=[1825, 1])
        .order_by("duration_days")
    )
    membership_plans = attach_effective_prices_for_user(user=request.user, plans=membership_plans)
    sim_ids = list(sims.values_list("id", flat=True))

    vehicles_by_sim_id = {
        vehicle.sim_id: vehicle
        for vehicle in Vehicle.objects.filter(sim_id__in=sim_ids).only(
            "sim_id", "brand", "model", "year", "imei_gps"
        )
    }
    cliente_ct = ContentType.objects.get_for_model(Cliente)
    sim_to_cliente_id = {}
    for assign in SIMAssignation.objects.filter(sim_id__in=sim_ids, content_type=cliente_ct).values("sim_id", "object_id"):
        sim_to_cliente_id.setdefault(assign["sim_id"], assign["object_id"])

    clientes_map = Cliente.objects.in_bulk(set(sim_to_cliente_id.values()))

    sim_cards = []
    for sim in sims:
        subscription = sim.current_subscription
        is_prepago = bool(subscription and _is_prepago_plan(subscription.plan))
        status_key = subscription.status if subscription else None
        vehicle = vehicles_by_sim_id.get(sim.id)
        vehicle_label = vehicle.get_vehicle() if vehicle else "-"
        cliente = clientes_map.get(sim_to_cliente_id.get(sim.id))
        days_left = None
        if subscription and subscription.end_date:
            days_left = max((subscription.end_date.date() - timezone.localdate()).days, 0)

        if selected_sub_status:
            if selected_sub_status == "none" and subscription is not None:
                continue
            if selected_sub_status != "none" and status_key != selected_sub_status:
                continue

        sim_cards.append(
            {
                "sim": sim,
                "subscription": subscription,
                "sim_status_label": lang["sim_states"].get(sim.status, sim.status),
                "vehicle_label": vehicle_label,
                "gps_imei": sim.display_imei or "-",
                "company_name": (cliente.company if cliente and cliente.company else "-"),
                "days_left": days_left,
                "is_prepago": is_prepago,
                "active_plan_label": (
                    lang["prepay_label"]
                    if subscription and _is_prepago_plan(subscription.plan)
                    else (subscription.plan.name if subscription else lang["no_subscription"])
                ),
                "subscription_status_key": status_key,
                "subscription_status_label": (
                    lang["subscription_states"].get(status_key, status_key)
                    if status_key
                    else "-"
                ),
            }
        )

    return render(
        request,
        "customer_portal/dashboard.html",
        {
            "sim_cards": sim_cards,
            "membership_plans": membership_plans,
            "lang": lang,
            "current_lang": request.user.preferred_lang,
            "q": query,
            "selected_sub_status": selected_sub_status,
        },
    )


@customer_required
def customer_sim_detail(request, sim_id):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims = get_client_sims(request.user)
    sim = get_object_or_404(sims, id=sim_id)
    subscription = sim.current_subscription
    status_key = subscription.status if subscription else None
    vehicle = Vehicle.objects.filter(sim=sim).only("brand", "model", "year").first()
    vehicle_label = vehicle.get_vehicle() if vehicle else "-"
    last_recharge = (
        SubscriptionPurchase.objects.filter(sim=sim, status="approved")
        .order_by("-updated_at")
        .only("updated_at")
        .first()
    )
    membership_plans = (
        MembershipPlan.objects.filter(is_active=True)
        .exclude(duration_days__in=[1825, 1])
        .order_by("duration_days")
    )
    membership_plans = attach_effective_prices_for_user(user=request.user, plans=membership_plans)
    subscription_plan_label = (
        lang["prepay_label"]
        if subscription and _is_prepago_plan(subscription.plan)
        else (subscription.plan.name if subscription else lang["no_subscription"])
    )

    return render(
        request,
        "customer_portal/sim_detail.html",
        {
            "sim": sim,
            "sim_status_label": lang["sim_states"].get(sim.status, sim.status),
            "subscription": subscription,
            "subscription_status_key": status_key,
            "subscription_status_label": (
                lang["subscription_states"].get(status_key, status_key)
                if status_key
                else lang["no_subscription"]
            ),
            "subscription_plan_label": subscription_plan_label,
            "vehicle_label": vehicle_label,
            "last_recharge": last_recharge.updated_at if last_recharge else None,
            "lang": lang,
            "current_lang": request.user.preferred_lang,
            "membership_plans": membership_plans,
            "auto_renew_enabled": bool(subscription and subscription.auto_renew),
        },
    )


@customer_required
@require_POST
def customer_create_checkout(request, sim_id):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims = get_client_sims(request.user)
    sim = get_object_or_404(sims, id=sim_id)

    plan_id = request.POST.get("plan_id")
    if not plan_id:
        messages.error(request, "Debes seleccionar un plan.")
        return redirect("customer_portal:sim_detail", sim_id=sim.id)

    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    if _is_prepago_plan(plan):
        messages.error(request, lang["prepay_not_available"])
        return redirect("customer_portal:sim_detail", sim_id=sim.id)

    base_url, notification_url = _get_payment_callback_urls(request)

    checkout_url = create_checkout_for_plan(
        user=request.user,
        sim=sim,
        plan=plan,
        base_url=base_url,
        notification_url=notification_url,
    )
    if not checkout_url:
        messages.error(request, "No se pudo iniciar el checkout de pago.")
        return redirect("customer_portal:sim_detail", sim_id=sim.id)

    return redirect(checkout_url)


@customer_required
@require_POST
def customer_toggle_auto_renew(request, sim_id):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims = get_client_sims(request.user)
    sim = get_object_or_404(sims, id=sim_id)
    subscription = sim.current_subscription
    if not subscription:
        messages.error(request, lang["auto_renew_requires_subscription"])
        return redirect("customer_portal:sim_detail", sim_id=sim.id)

    effective_price, _ = resolve_plan_price_for_user(user=request.user, plan=subscription.plan)
    if _is_prepago_plan(subscription.plan) or effective_price <= 0:
        messages.error(request, lang["auto_renew_not_supported_plan"])
        return redirect("customer_portal:sim_detail", sim_id=sim.id)

    action = (request.POST.get("action") or "").strip().lower()
    if action == "enable":
        base_url, notification_url = _get_payment_callback_urls(request)
        init_point = create_auto_renew_checkout_for_subscription(
            user=request.user,
            subscription=subscription,
            base_url=base_url,
            notification_url=notification_url,
        )
        if not init_point:
            messages.error(request, lang["auto_renew_setup_failed"])
            return redirect("customer_portal:sim_detail", sim_id=sim.id)
        return redirect(init_point)

    if action == "disable":
        if disable_subscription_auto_renew(subscription):
            messages.success(request, lang["auto_renew_disabled"])
        else:
            messages.error(request, lang["auto_renew_disable_failed"])
        return redirect("customer_portal:sim_detail", sim_id=sim.id)

    messages.error(request, lang["auto_renew_invalid_action"])
    return redirect("customer_portal:sim_detail", sim_id=sim.id)


@customer_required
@require_POST
def customer_bulk_checkout_preview(request):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims, plan = _get_valid_bulk_selection(request, lang)
    if not sims:
        return redirect("customer_portal:dashboard")

    vehicles_by_sim_id = {
        vehicle.sim_id: vehicle
        for vehicle in Vehicle.objects.filter(sim_id__in=[sim.id for sim in sims]).only("sim_id", "brand", "model", "year")
    }
    effective_price, _ = resolve_plan_price_for_user(user=request.user, plan=plan)
    line_items = []
    for sim in sims:
        vehicle = vehicles_by_sim_id.get(sim.id)
        line_items.append(
            {
                "sim": sim,
                "vehicle_label": vehicle.get_vehicle() if vehicle else "-",
                "amount": effective_price,
            }
        )

    total_amount = sum((item["amount"] for item in line_items), 0)
    return render(
        request,
        "customer_portal/bulk_checkout_confirm.html",
        {
            "lang": lang,
            "current_lang": request.user.preferred_lang,
            "plan": plan,
            "line_items": line_items,
            "total_amount": total_amount,
        },
    )


@customer_required
@require_POST
def customer_bulk_checkout(request):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims, plan = _get_valid_bulk_selection(request, lang)
    if not sims:
        return redirect("customer_portal:dashboard")

    base_url, notification_url = _get_payment_callback_urls(request)

    checkout_url = create_checkout_for_bulk_plan(
        user=request.user,
        sims=sims,
        plan=plan,
        base_url=base_url,
        notification_url=notification_url,
    )
    if not checkout_url:
        messages.error(request, lang["bulk_checkout_failed"])
        return redirect("customer_portal:dashboard")

    return redirect(checkout_url)


@customer_required
def payment_success(request):
    messages.success(request, "Pago aprobado. Tu suscripción se actualizará en breve.")
    return redirect("customer_portal:dashboard")


@customer_required
def payment_pending(request):
    messages.warning(request, "Pago pendiente. Se actualizará cuando Mercado Pago lo confirme.")
    return redirect("customer_portal:dashboard")


@customer_required
def payment_failure(request):
    messages.error(request, "El pago no fue aprobado.")
    return redirect("customer_portal:dashboard")


@csrf_exempt
def payment_webhook(request):
    if request.method != "POST":
        create_log(
            log_type="SYSTEM",
            severity="WARNING",
            message="Webhook rejected due to invalid method",
            metadata={"method": request.method, "client_ip": get_client_ip(request)},
        )
        return HttpResponseBadRequest("Invalid method")

    configured_webhook_token = (getattr(settings, "MERCADOPAGO_WEBHOOK_TOKEN", "") or "").strip()
    if configured_webhook_token:
        provided_token = (
            request.headers.get("X-Webhook-Token")
            or request.GET.get("token")
            or request.POST.get("token")
            or ""
        ).strip()
        if not hmac.compare_digest(provided_token, configured_webhook_token):
            create_log(
                log_type="SYSTEM",
                severity="WARNING",
                message="Webhook rejected due to invalid token",
                metadata={"client_ip": get_client_ip(request)},
            )
            return HttpResponseBadRequest("Invalid webhook token")

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        create_log(
            log_type="SYSTEM",
            severity="WARNING",
            message="Webhook rejected due to invalid JSON",
            metadata={"client_ip": get_client_ip(request)},
        )
        return HttpResponseBadRequest("Invalid JSON")

    payment_id = str((payload.get("data") or {}).get("id") or "")
    event_type = payload.get("type") or payload.get("topic")
    create_log(
        log_type="SYSTEM",
        message="Webhook received",
        reference_id=payment_id or None,
        metadata={
            "event_type": event_type,
            "action": payload.get("action"),
            "payment_id": payment_id or None,
            "live_mode": payload.get("live_mode"),
            "user_id": payload.get("user_id"),
            "client_ip": get_client_ip(request),
        },
    )
    if event_type in {"preapproval", "subscription_preapproval"} and payment_id:
        process_mercadopago_preapproval(payment_id)
        return HttpResponse("ok", status=200)

    if event_type != "payment" or not payment_id:
        return HttpResponse("ok", status=200)

    process_mercadopago_payment(payment_id)
    return HttpResponse("ok", status=200)
