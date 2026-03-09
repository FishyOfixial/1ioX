from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from billing.models import CustomerPlanPriceOverride, MembershipPlan


def resolve_plan_price_for_user(*, user, plan: MembershipPlan) -> tuple[Decimal, CustomerPlanPriceOverride | None]:
    base_price = plan.price or Decimal("0")
    if user is None:
        return base_price, None

    override = (
        CustomerPlanPriceOverride.objects.filter(user=user, plan=plan, is_active=True)
        .select_related("plan")
        .first()
    )
    if not override:
        return base_price, None

    multiplier = Decimal("1") + (override.adjustment_percent / Decimal("100"))
    effective_price = (base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if effective_price < Decimal("0"):
        effective_price = Decimal("0.00")
    return effective_price, override


def attach_effective_prices_for_user(*, user, plans: Iterable[MembershipPlan]) -> list[MembershipPlan]:
    plans_list = list(plans)
    if user is None or not plans_list:
        for plan in plans_list:
            plan.effective_price = plan.price
            plan.adjustment_percent = Decimal("0.00")
        return plans_list

    plan_ids = [plan.id for plan in plans_list]
    override_map = {
        override.plan_id: override
        for override in CustomerPlanPriceOverride.objects.filter(
            user=user,
            plan_id__in=plan_ids,
            is_active=True,
        )
    }

    for plan in plans_list:
        base_price = plan.price or Decimal("0")
        override = override_map.get(plan.id)
        if not override:
            plan.effective_price = base_price
            plan.adjustment_percent = Decimal("0.00")
            continue
        multiplier = Decimal("1") + (override.adjustment_percent / Decimal("100"))
        effective_price = (base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        plan.effective_price = max(effective_price, Decimal("0.00"))
        plan.adjustment_percent = override.adjustment_percent

    return plans_list
