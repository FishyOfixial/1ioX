from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Q, Sum
from django.utils import timezone

from billing.models import CommissionPeriod, DistributorSale
from SIM_Control.models import Cliente, Distribuidor, Revendedor

COMMISSION_RATE = Decimal("0.25")
MONEY = Decimal("0.01")


@dataclass(frozen=True)
class Seller:
    seller_type: str
    profile: Distribuidor | Revendedor


def previous_month(today=None) -> tuple[int, int]:
    today = today or timezone.localdate()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def period_string(year: int, month: int) -> str:
    return f"{int(year):04d}-{int(month):02d}"


def calculate_commission(total: Decimal) -> Decimal:
    return ((total or Decimal("0.00")) * COMMISSION_RATE).quantize(MONEY, rounding=ROUND_HALF_UP)


def _approved_sales_for_period(year: int, month: int):
    return DistributorSale.objects.select_related("purchase", "cliente", "plan", "distribuidor", "revendedor").filter(
        status="approved",
        period=period_string(year, month),
    )


def seller_sales_qs(seller_type: str, seller_id: int, year: int, month: int):
    sales = _approved_sales_for_period(year, month)
    if seller_type == "revendedor":
        return sales.filter(
            Q(purchase__mp_account_type="revendedor", purchase__mp_account_id=seller_id)
            | Q(purchase__mp_account_type__isnull=True, revendedor_id=seller_id)
            | Q(purchase__mp_account_type="", revendedor_id=seller_id)
        )
    return sales.filter(
        Q(purchase__mp_account_type="distribuidor", purchase__mp_account_id=seller_id)
        | Q(purchase__mp_account_type__isnull=True, distribuidor_id=seller_id, revendedor__isnull=True)
        | Q(purchase__mp_account_type="", distribuidor_id=seller_id, revendedor__isnull=True)
    )


def get_seller(seller_type: str, seller_id: int) -> Seller:
    if seller_type == "revendedor":
        return Seller(seller_type=seller_type, profile=Revendedor.objects.get(id=seller_id))
    return Seller(seller_type="distribuidor", profile=Distribuidor.objects.get(id=seller_id))


def seller_label(seller: Seller) -> str:
    company = (seller.profile.company or "").strip()
    name = f"{seller.profile.first_name} {seller.profile.last_name}".strip()
    return company or name or str(seller.profile)


def sync_commission_for_seller(seller_type: str, seller_id: int, year: int, month: int) -> CommissionPeriod:
    seller = get_seller(seller_type, seller_id)
    sales = seller_sales_qs(seller_type, seller_id, year, month)
    totals = sales.aggregate(total=Sum("amount"), count=Count("id"))
    total_sold = (totals["total"] or Decimal("0.00")).quantize(MONEY, rounding=ROUND_HALF_UP)
    renewal_count = int(totals["count"] or 0)
    commission = calculate_commission(total_sold)

    lookup = {"year": year, "month": month}
    if seller_type == "revendedor":
        lookup["revendedor"] = seller.profile
        defaults = {"distribuidor": None}
    else:
        lookup["distribuidor"] = seller.profile
        defaults = {"revendedor": None}

    existing = CommissionPeriod.objects.filter(**lookup).first()
    default_status = CommissionPeriod.STATUS_PAID if commission <= 0 else CommissionPeriod.STATUS_PENDING
    defaults.update(
        {
            "total_vendido": total_sold,
            "comision_calculada": commission,
            "renewal_count": renewal_count,
            "status": existing.status if existing else default_status,
        }
    )
    if existing and existing.status == CommissionPeriod.STATUS_PAID and commission > 0:
        defaults["paid_at"] = existing.paid_at
        defaults["marked_by"] = existing.marked_by

    commission_period, _created = CommissionPeriod.objects.update_or_create(defaults=defaults, **lookup)
    return commission_period


def all_sellers():
    for distribuidor in Distribuidor.objects.select_related("user").order_by("company", "first_name", "last_name"):
        yield Seller("distribuidor", distribuidor)
    for revendedor in Revendedor.objects.select_related("user", "distribuidor").order_by("company", "first_name", "last_name"):
        yield Seller("revendedor", revendedor)


def sync_commissions_for_period(year: int, month: int):
    return [sync_commission_for_seller(seller.seller_type, seller.profile.id, year, month) for seller in all_sellers()]


def get_commission_record_for_user(user, year: int, month: int) -> CommissionPeriod | None:
    if user.user_type == "DISTRIBUIDOR":
        profile = Distribuidor.objects.filter(user=user).first()
        return sync_commission_for_seller("distribuidor", profile.id, year, month) if profile else None
    if user.user_type == "REVENDEDOR":
        profile = Revendedor.objects.filter(user=user).first()
        return sync_commission_for_seller("revendedor", profile.id, year, month) if profile else None
    return None


def get_blocking_commission_for_user(user) -> CommissionPeriod | None:
    if not user.is_authenticated or user.user_type not in {"DISTRIBUIDOR", "REVENDEDOR"}:
        return None
    if user.user_type == "DISTRIBUIDOR":
        profile = Distribuidor.objects.filter(user=user).first()
        if not profile:
            return None
        return CommissionPeriod.objects.filter(distribuidor=profile, status=CommissionPeriod.STATUS_BLOCKED).first()
    profile = Revendedor.objects.filter(user=user).first()
    if not profile:
        return None
    return CommissionPeriod.objects.filter(revendedor=profile, status=CommissionPeriod.STATUS_BLOCKED).first()


def get_blocking_commission_for_customer(user) -> CommissionPeriod | None:
    cliente = Cliente.objects.filter(user=user).select_related("distribuidor", "revendedor").first()
    if not cliente:
        return None
    if cliente.revendedor:
        blocked = CommissionPeriod.objects.filter(revendedor=cliente.revendedor, status=CommissionPeriod.STATUS_BLOCKED).first()
        if blocked:
            return blocked
    if cliente.distribuidor:
        return CommissionPeriod.objects.filter(distribuidor=cliente.distribuidor, status=CommissionPeriod.STATUS_BLOCKED).first()
    return None


def should_show_previous_month_alert(today=None) -> bool:
    today = today or timezone.localdate()
    return 1 <= today.day <= 7


def get_previous_month_alert_for_user(user, today=None) -> CommissionPeriod | None:
    if not should_show_previous_month_alert(today):
        return None
    year, month = previous_month(today)
    record = get_commission_record_for_user(user, year, month)
    if record and record.status == CommissionPeriod.STATUS_PENDING and record.comision_calculada > 0:
        return record
    return None


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)
