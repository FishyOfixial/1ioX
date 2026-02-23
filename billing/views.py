from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from SIM_Control.models import SimCard
from billing.models import MembershipPlan, Subscription


def _sim_detail_redirect(sim):
    return redirect("sim_details", iccid=sim.iccid)


@login_required
@require_POST
def assign_plan(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    current_subscription = sim.current_subscription
    if current_subscription is not None:
        messages.warning(request, "La SIM ya tiene una suscripción activa.")
        return _sim_detail_redirect(sim)

    plan_id = request.POST.get("plan_id")
    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    subscription = Subscription.objects.create(
        sim=sim,
        plan=plan,
        start_date=timezone.now(),
        status="active",
        auto_renew=False,
    )
    subscription.activate()
    messages.success(request, "Plan asignado correctamente.")
    return _sim_detail_redirect(sim)


@login_required
@require_POST
def renew(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    subscription = sim.current_subscription
    if subscription is None:
        messages.error(request, "La SIM no tiene una suscripción para renovar.")
        return _sim_detail_redirect(sim)

    subscription.extend()
    messages.success(request, "Suscripción renovada correctamente.")
    return _sim_detail_redirect(sim)


@login_required
@require_POST
def change_plan(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    subscription = sim.current_subscription
    if subscription is None:
        messages.error(request, "La SIM no tiene una suscripción para cambiar.")
        return _sim_detail_redirect(sim)

    plan_id = request.POST.get("plan_id")
    new_plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)
    subscription.overwrite_plan(new_plan)
    messages.success(request, "Plan cambiado correctamente.")
    return _sim_detail_redirect(sim)


@login_required
@require_POST
def suspend(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    subscription = sim.current_subscription
    if subscription is None:
        messages.error(request, "La SIM no tiene una suscripción para suspender.")
        return _sim_detail_redirect(sim)

    subscription.suspend()
    messages.success(request, "Suscripción suspendida.")
    return _sim_detail_redirect(sim)


@login_required
@require_POST
def cancel(request, sim_id):
    sim = get_object_or_404(SimCard, id=sim_id)
    subscription = sim.current_subscription
    if subscription is None:
        messages.error(request, "La SIM no tiene una suscripción para cancelar.")
        return _sim_detail_redirect(sim)

    subscription.cancel()
    messages.success(request, "Suscripción cancelada.")
    return _sim_detail_redirect(sim)
