from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from SIM_Control.decorators import matriz_required
from SIM_Control.models import SimCard
from auditlogs.utils import create_log
from billing.models import MembershipPlan, Subscription
from billing.services.subscription_api_sync import ensure_sim_disabled, ensure_sim_enabled
from billing.services.subscription_dates import calculate_new_end_date, normalize_to_midday
from customer_portal.services.payments_service import disable_subscription_auto_renew


def _sim_detail_redirect(sim):
    return redirect("sim_details", iccid=sim.iccid)


class _CustomDurationPlan:
    period_unit = "day"

    def __init__(self, period_count):
        self.period_count = period_count
        self.duration_days = period_count


def _get_prepago_plan():
    prepago_plan = (
        MembershipPlan.objects.filter(is_active=True)
        .filter(Q(name__iexact="Prepago") | Q(name__iexact="5 Años"))
        .order_by("duration_days")
        .first()
    )
    if prepago_plan:
        return prepago_plan
    return MembershipPlan.objects.filter(is_active=True).order_by("duration_days").first()


def _resolve_requested_plan(request):
    custom_days_raw = (request.POST.get("custom_days") or "").strip()
    if custom_days_raw:
        try:
            custom_days = int(custom_days_raw)
        except ValueError as exc:
            raise ValueError("Los dias personalizados deben ser un numero entero.") from exc

        if not 1 <= custom_days <= 1825:
            raise ValueError("El plan personalizado debe estar entre 1 y 1825 dias.")

        base_plan = _get_prepago_plan()
        if base_plan is None:
            raise ValueError("No hay planes disponibles para asignar.")
        return base_plan, custom_days

    plan_id = request.POST.get("plan_id")
    if not plan_id:
        raise ValueError("Debes seleccionar un plan o capturar dias personalizados.")
    return get_object_or_404(MembershipPlan, id=plan_id, is_active=True), None


def _apply_custom_days_overwrite(subscription, base_plan, custom_days):
    start_date = normalize_to_midday(timezone.now())
    custom_plan = _CustomDurationPlan(custom_days)
    subscription.plan = base_plan
    subscription.start_date = start_date
    subscription.end_date = calculate_new_end_date(start_date, custom_plan)
    subscription.status = "active"
    subscription.save(update_fields=["plan", "start_date", "end_date", "status"])


def _apply_custom_days_extend(subscription, base_plan, custom_days):
    now = timezone.now()
    if subscription.end_date and subscription.end_date > now:
        base_date = subscription.end_date
    else:
        base_date = now
        subscription.start_date = normalize_to_midday(now)

    custom_plan = _CustomDurationPlan(custom_days)
    subscription.plan = base_plan
    subscription.end_date = calculate_new_end_date(base_date, custom_plan)
    subscription.status = "active"
    subscription.save(update_fields=["plan", "start_date", "end_date", "status"])


@matriz_required
@require_POST
def assign_plan(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    current_subscription = sim.current_subscription
    if current_subscription is not None:
        messages.warning(request, "La SIM ya tiene una suscripcion activa.")
        return _sim_detail_redirect(sim)

    try:
        plan, custom_days = _resolve_requested_plan(request)
    except ValueError as exc:
        messages.error(request, str(exc))
        return _sim_detail_redirect(sim)

    subscription = Subscription.objects.create(
        sim=sim,
        plan=plan,
        start_date=timezone.now(),
        status="active",
        auto_renew=False,
    )

    if custom_days:
        custom_plan = _CustomDurationPlan(custom_days)
        subscription.end_date = calculate_new_end_date(subscription.start_date, custom_plan)
        subscription.save(update_fields=["end_date"])

    subscription.activate()
    create_log(
        log_type="SUBSCRIPTION",
        user=request.user,
        message="SIM activation requested from billing assign plan",
        reference_id=str(subscription.id),
        metadata={"sim_iccid": sim.iccid, "plan": plan.name},
    )
    if not ensure_sim_enabled(subscription):
        messages.warning(request, "Plan asignado, pero no se pudo sincronizar la SIM con 1NCE.")
    messages.success(request, "Plan asignado correctamente.")
    return _sim_detail_redirect(sim)


@matriz_required
@require_POST
def renew(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    subscription = sim.current_subscription
    if subscription is None:
        messages.error(request, "La SIM no tiene una suscripcion para renovar.")
        return _sim_detail_redirect(sim)

    has_plan_input = bool((request.POST.get("plan_id") or "").strip() or (request.POST.get("custom_days") or "").strip())
    if has_plan_input:
        try:
            selected_plan, custom_days = _resolve_requested_plan(request)
        except ValueError as exc:
            messages.error(request, str(exc))
            return _sim_detail_redirect(sim)
    else:
        selected_plan, custom_days = subscription.plan, None

    if custom_days:
        _apply_custom_days_extend(subscription, selected_plan, custom_days)
    else:
        subscription.extend(plan=selected_plan)
    create_log(
        log_type="SUBSCRIPTION",
        user=request.user,
        message="Subscription renewal requested",
        reference_id=str(subscription.id),
        metadata={"sim_iccid": sim.iccid, "plan": selected_plan.name},
    )

    if not ensure_sim_enabled(subscription):
        messages.warning(request, "Suscripcion renovada, pero no se pudo sincronizar la SIM con 1NCE.")
    messages.success(request, "Suscripcion renovada correctamente.")
    return _sim_detail_redirect(sim)


@matriz_required
@require_POST
def change_plan(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    subscription = sim.current_subscription
    if subscription is None:
        messages.error(request, "La SIM no tiene una suscripcion para cambiar.")
        return _sim_detail_redirect(sim)

    try:
        new_plan, custom_days = _resolve_requested_plan(request)
    except ValueError as exc:
        messages.error(request, str(exc))
        return _sim_detail_redirect(sim)

    if custom_days:
        _apply_custom_days_overwrite(subscription, new_plan, custom_days)
    else:
        subscription.overwrite_plan(new_plan)
    create_log(
        log_type="SUBSCRIPTION",
        user=request.user,
        message="Subscription plan change requested",
        reference_id=str(subscription.id),
        metadata={"sim_iccid": sim.iccid, "plan": new_plan.name},
    )

    if not ensure_sim_enabled(subscription):
        messages.warning(request, "Plan cambiado, pero no se pudo sincronizar la SIM con 1NCE.")
    messages.success(request, "Plan cambiado correctamente.")
    return _sim_detail_redirect(sim)


@matriz_required
@require_POST
def suspend(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    subscription = sim.current_subscription
    if subscription is None:
        messages.error(request, "La SIM no tiene una suscripcion para suspender.")
        return _sim_detail_redirect(sim)

    if subscription.auto_renew:
        disable_subscription_auto_renew(subscription)
    subscription.suspend()
    create_log(
        log_type="SUBSCRIPTION",
        severity="WARNING",
        user=request.user,
        message="Subscription suspension requested",
        reference_id=str(subscription.id),
        metadata={"sim_iccid": sim.iccid},
    )
    if not ensure_sim_disabled(subscription):
        messages.warning(request, "Suscripcion suspendida, pero no se pudo sincronizar la SIM con 1NCE.")
    messages.success(request, "Suscripcion suspendida.")
    return _sim_detail_redirect(sim)


@matriz_required
@require_POST
def cancel(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    subscription = sim.current_subscription
    if subscription is None:
        messages.error(request, "La SIM no tiene una suscripcion para cancelar.")
        return _sim_detail_redirect(sim)

    if subscription.auto_renew:
        disable_subscription_auto_renew(subscription)
    subscription.cancel()
    create_log(
        log_type="SUBSCRIPTION",
        severity="WARNING",
        user=request.user,
        message="Subscription cancellation requested",
        reference_id=str(subscription.id),
        metadata={"sim_iccid": sim.iccid},
    )
    if not ensure_sim_disabled(subscription):
        messages.warning(request, "Suscripcion cancelada, pero no se pudo sincronizar la SIM con 1NCE.")
    messages.success(request, "Suscripcion cancelada.")
    return _sim_detail_redirect(sim)
