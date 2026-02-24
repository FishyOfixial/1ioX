import json
import hmac

from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from billing.models import MembershipPlan, SubscriptionPurchase
from SIM_Control.models import Vehicle
from customer_portal.decorators import customer_required
from customer_portal.services.payments_service import (
    create_checkout_for_bulk_plan,
    create_checkout_for_plan,
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


@customer_required
def customer_dashboard(request):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims = get_client_sims(request.user)
    query = (request.GET.get("q") or "").strip()
    selected_sub_status = (request.GET.get("sub_status") or "").strip()

    if query:
        sims = sims.filter(iccid__icontains=query)

    membership_plans = MembershipPlan.objects.filter(is_active=True).exclude(duration_days=1825).order_by("duration_days")

    vehicles_by_sim_id = {
        vehicle.sim_id: vehicle
        for vehicle in Vehicle.objects.filter(sim_id__in=sims.values_list("id", flat=True)).only(
            "sim_id", "brand", "model", "year"
        )
    }

    sim_cards = []
    for sim in sims:
        subscription = sim.current_subscription
        status_key = subscription.status if subscription else None
        vehicle = vehicles_by_sim_id.get(sim.id)
        vehicle_label = vehicle.get_vehicle() if vehicle else "-"

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
    membership_plans = MembershipPlan.objects.filter(is_active=True).exclude(duration_days=1825).order_by("duration_days")
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

    base_url = request.build_absolute_uri("/").rstrip("/")
    notification_url = request.build_absolute_uri("/portal/billing/mercadopago/notification/")

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
def customer_bulk_checkout_preview(request):
    lang = LANG_PORTAL.get(request.user.preferred_lang, LANG_PORTAL["es"])
    sims, plan = _get_valid_bulk_selection(request, lang)
    if not sims:
        return redirect("customer_portal:dashboard")

    vehicles_by_sim_id = {
        vehicle.sim_id: vehicle
        for vehicle in Vehicle.objects.filter(sim_id__in=[sim.id for sim in sims]).only("sim_id", "brand", "model", "year")
    }
    line_items = []
    for sim in sims:
        vehicle = vehicles_by_sim_id.get(sim.id)
        line_items.append(
            {
                "sim": sim,
                "vehicle_label": vehicle.get_vehicle() if vehicle else "-",
                "amount": plan.price or 0,
            }
        )

    total_amount = (plan.price or 0) * len(line_items)
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

    base_url = request.build_absolute_uri("/").rstrip("/")
    notification_url = request.build_absolute_uri("/portal/billing/mercadopago/notification/")

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
            return HttpResponseBadRequest("Invalid webhook token")

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    payment_id = str((payload.get("data") or {}).get("id") or "")
    event_type = payload.get("type") or payload.get("topic")

    if event_type != "payment" or not payment_id:
        return HttpResponse("ok", status=200)

    process_mercadopago_payment(payment_id)
    return HttpResponse("ok", status=200)
