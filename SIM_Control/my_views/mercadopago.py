import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from auditlogs.utils import create_log
from billing.models import CommissionPeriod, DistributorSale
from billing.services.commissions import (
    COMMISSION_RATE,
    all_sellers,
    calculate_net_utility,
    calculate_commission,
    create_commission_checkout,
    get_blocking_commission_for_user,
    get_commission_record_for_user,
    get_seller,
    previous_month,
    seller_label,
    seller_sales_qs,
    sync_commission_for_seller,
    sync_commissions_for_period,
)
from billing.services.mercadopago_oauth import (
    MercadoPagoOAuthError,
    build_authorization_url,
    exchange_code_for_tokens,
    get_profile_from_state,
    save_tokens,
    validate_state,
)
from SIM_Control.decorators import matriz_required, user_in
from SIM_Control.models import Distribuidor, Revendedor
from SIM_Control.my_views.translations import get_translation
from SIM_Control.security import get_public_base_url

logger = logging.getLogger("billing.mercadopago")


def _current_profile(user):
    if user.user_type == "DISTRIBUIDOR":
        return Distribuidor.objects.filter(user=user).first()
    if user.user_type == "REVENDEDOR":
        return Revendedor.objects.filter(user=user).first()
    return None


def _parse_period(request):
    today = timezone.localdate()
    default_year, default_month = previous_month(today)
    try:
        month = int(request.GET.get("month") or default_month)
        year = int(request.GET.get("year") or default_year)
    except (TypeError, ValueError):
        month = default_month
        year = default_year
    month = min(max(month, 1), 12)
    return year, month


def _years_for_filter():
    today = timezone.localdate()
    return [today.year + offset for offset in range(-3, 2)]


def _status_label(status):
    return {
        CommissionPeriod.STATUS_PENDING: "Pendiente",
        CommissionPeriod.STATUS_PAID: "Pagado",
        CommissionPeriod.STATUS_BLOCKED: "Bloqueado",
    }.get(status, status)


@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def mercado_pago_connect(request):
    profile = _current_profile(request.user)
    if not profile:
        messages.error(request, "No se encontro el perfil para conectar Mercado Pago.")
        return redirect("dashboard")

    try:
        return redirect(build_authorization_url(request=request, profile=profile))
    except MercadoPagoOAuthError:
        logger.exception("mercadopago_oauth_start_failed user_id=%s", request.user.id)
        messages.error(request, "No se pudo iniciar la conexion con Mercado Pago.")
        return redirect("mercado_pago_report")


@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def mercado_pago_callback(request):
    error = request.GET.get("error")
    if error:
        create_log(
            log_type="BILLING",
            severity="WARNING",
            user=request.user,
            message="Mercado Pago OAuth authorization rejected",
            metadata={"error": error, "error_description": request.GET.get("error_description")},
        )
        messages.error(request, "Mercado Pago no autorizo la conexion.")
        return redirect("mercado_pago_report")

    code = (request.GET.get("code") or "").strip()
    state = (request.GET.get("state") or "").strip()
    if not code:
        messages.error(request, "Mercado Pago no envio un codigo de autorizacion.")
        return redirect("mercado_pago_report")

    try:
        state_data = validate_state(request=request, received_state=state)
        profile = get_profile_from_state(state_data)
        if profile.user_id != request.user.id and request.user.user_type != "MATRIZ":
            raise MercadoPagoOAuthError("OAuth profile does not belong to current user")
        tokens = exchange_code_for_tokens(code)
        save_tokens(profile, tokens)
    except MercadoPagoOAuthError:
        logger.exception("mercadopago_oauth_callback_failed user_id=%s", request.user.id)
        messages.error(request, "No se pudo completar la conexion con Mercado Pago.")
        return redirect("mercado_pago_report")

    create_log(
        log_type="BILLING",
        severity="INFO",
        user=request.user,
        reference_id=str(profile.id),
        message="Mercado Pago account connected",
        metadata={"profile": profile.__class__.__name__, "mercado_pago_user_id": profile.mercado_pago_user_id},
    )
    messages.success(request, "Mercado Pago conectado correctamente.")
    return redirect("mercado_pago_report")


@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def mercado_pago_report(request):
    if request.user.user_type == "MATRIZ":
        return redirect("mercado_pago_commissions")

    lang, base = get_translation(request.user, "dashboard")
    year, month_int = _parse_period(request)
    month = f"{month_int:02d}"
    period = f"{year}-{month}"

    profile = _current_profile(request.user)
    seller_type = request.user.user_type.lower()
    sales = seller_sales_qs(seller_type, profile.id, year, month_int) if profile else DistributorSale.objects.none()

    total = sales.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    commission_record = get_commission_record_for_user(request.user, year, month_int)
    current_profile = _current_profile(request.user)
    return render(
        request,
        "mercadopago_report.html",
        {
            "base": base,
            "lang": lang,
            "sales": sales.order_by("-paid_at"),
            "total": total,
            "commission_record": commission_record,
            "commission": calculate_commission(total),
            "net_utility": calculate_net_utility(total),
            "period": period,
            "selected_month": month,
            "selected_year": year,
            "months": [f"{number:02d}" for number in range(1, 13)],
            "years": _years_for_filter(),
            "mercado_pago_profile": current_profile,
            "commission_rate_percent": int(COMMISSION_RATE * Decimal("100")),
        },
    )


@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
@require_POST
def mercado_pago_pay_commission(request):
    try:
        year = int(request.POST.get("year"))
        month = int(request.POST.get("month"))
    except (TypeError, ValueError):
        year, month = previous_month()

    record = get_commission_record_for_user(request.user, year, month)
    if not record or record.comision_calculada <= 0:
        messages.error(request, "No hay comision pendiente para pagar en este periodo.")
        return redirect("mercado_pago_report")
    if record.status == CommissionPeriod.STATUS_PAID:
        messages.info(request, "Esta comision ya esta marcada como pagada.")
        return redirect("mercado_pago_report")

    base_url = get_public_base_url(request)
    notification_url = f"{base_url}/billing/mercadopago/notification/"
    checkout_url = create_commission_checkout(
        record=record,
        user=request.user,
        base_url=base_url,
        notification_url=notification_url,
    )
    if not checkout_url:
        messages.error(request, "No se pudo iniciar el pago de comision.")
        return redirect("mercado_pago_report")
    return redirect(checkout_url)


@login_required
@matriz_required
def mercado_pago_commissions(request):
    lang, base = get_translation(request.user, "dashboard")
    year, month = _parse_period(request)
    status_filter = (request.GET.get("status") or "").strip()
    seller_filter = (request.GET.get("seller") or "").strip()

    records = sync_commissions_for_period(year, month)
    if status_filter:
        records = [record for record in records if record.status == status_filter]
    if seller_filter and ":" in seller_filter:
        seller_type, seller_id = seller_filter.split(":", 1)
        try:
            seller_id_int = int(seller_id)
            records = [
                record
                for record in records
                if record.seller_type == seller_type and record.seller and record.seller.id == seller_id_int
            ]
        except ValueError:
            pass

    rows = []
    for record in records:
        seller = record.seller
        rows.append(
            {
                "record": record,
                "seller_type": record.seller_type,
                "seller_id": seller.id if seller else None,
                "seller_label": seller_label(get_seller(record.seller_type, seller.id)) if seller else "-",
                "status_label": _status_label(record.status),
            }
        )
    rows.sort(key=lambda row: (row["seller_type"], row["seller_label"].lower()))
    total_sold = sum((row["record"].total_vendido for row in rows), Decimal("0.00"))
    total_commission = sum((row["record"].comision_calculada for row in rows), Decimal("0.00"))
    total_renewals = sum((row["record"].renewal_count for row in rows), 0)
    blocked_count = sum(1 for row in rows if row["record"].status == CommissionPeriod.STATUS_BLOCKED)

    seller_options = [
        {
            "value": f"{seller.seller_type}:{seller.profile.id}",
            "label": f"{'Revendedor' if seller.seller_type == 'revendedor' else 'Distribuidor'} - {seller_label(seller)}",
        }
        for seller in all_sellers()
    ]

    return render(
        request,
        "mercadopago_commissions.html",
        {
            "base": base,
            "lang": lang,
            "rows": rows,
            "selected_month": f"{month:02d}",
            "selected_year": year,
            "months": [f"{number:02d}" for number in range(1, 13)],
            "years": _years_for_filter(),
            "statuses": [
                (CommissionPeriod.STATUS_PENDING, "Pendiente"),
                (CommissionPeriod.STATUS_PAID, "Pagado"),
                (CommissionPeriod.STATUS_BLOCKED, "Bloqueado"),
            ],
            "selected_status": status_filter,
            "seller_options": seller_options,
            "selected_seller": seller_filter,
            "commission_rate_percent": int(COMMISSION_RATE * Decimal("100")),
            "total_sold": total_sold,
            "total_commission": total_commission,
            "total_renewals": total_renewals,
            "blocked_count": blocked_count,
        },
    )


@login_required
@matriz_required
def mercado_pago_commission_detail(request, seller_type, seller_id):
    lang, base = get_translation(request.user, "dashboard")
    year, month = _parse_period(request)
    seller = get_seller(seller_type, seller_id)
    record = sync_commission_for_seller(seller.seller_type, seller.profile.id, year, month)
    sales = seller_sales_qs(seller.seller_type, seller.profile.id, year, month).order_by("-paid_at")
    total = sales.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return render(
        request,
        "mercadopago_commission_detail.html",
        {
            "base": base,
            "lang": lang,
            "record": record,
            "sales": sales,
            "seller_type": seller.seller_type,
            "seller_id": seller.profile.id,
            "seller_label": seller_label(seller),
            "selected_month": f"{month:02d}",
            "selected_year": year,
            "total": total,
            "commission": calculate_commission(total),
            "commission_rate_percent": int(COMMISSION_RATE * Decimal("100")),
            "status_label": _status_label(record.status),
        },
    )


@login_required
@matriz_required
@require_POST
def mercado_pago_commission_action(request, seller_type, seller_id):
    try:
        year = int(request.POST.get("year"))
        month = int(request.POST.get("month"))
    except (TypeError, ValueError):
        today = timezone.localdate()
        year, month = today.year, today.month

    seller = get_seller(seller_type, seller_id)
    record = sync_commission_for_seller(seller.seller_type, seller.profile.id, year, month)
    action = (request.POST.get("action") or "").strip().lower()
    notes = (request.POST.get("notes") or "").strip()

    if action == "mark_paid":
        record.status = CommissionPeriod.STATUS_PAID
        record.paid_at = timezone.now()
        record.marked_by = request.user
        messages.success(request, "Comision marcada como pagada.")
    elif action == "block":
        record.status = CommissionPeriod.STATUS_BLOCKED
        record.marked_by = request.user
        messages.warning(request, "Cuenta bloqueada por adeudo de comision.")
    elif action == "unblock":
        record.status = CommissionPeriod.STATUS_PENDING if record.comision_calculada > 0 else CommissionPeriod.STATUS_PAID
        record.marked_by = request.user
        if record.status == CommissionPeriod.STATUS_PAID and not record.paid_at:
            record.paid_at = timezone.now()
        messages.success(request, "Cuenta desbloqueada.")
    else:
        messages.error(request, "Accion no valida.")
        return redirect("mercado_pago_commission_detail", seller_type=seller.seller_type, seller_id=seller.profile.id)

    if notes:
        record.notes = notes
    record.save(update_fields=["status", "paid_at", "marked_by", "notes", "updated_at"])
    create_log(
        log_type="BILLING",
        severity="WARNING" if action == "block" else "INFO",
        user=request.user,
        reference_id=str(record.id),
        message="Commission status updated",
        metadata={
            "seller_type": seller.seller_type,
            "seller_id": seller.profile.id,
            "period": record.period_label,
            "action": action,
            "status": record.status,
        },
    )
    return redirect(
        f"{request.POST.get('next') or ''}"
        or "mercado_pago_commissions"
    )


@login_required
@user_in("DISTRIBUIDOR", "REVENDEDOR")
def commission_blocked(request):
    lang, base = get_translation(request.user, "dashboard")
    record = get_blocking_commission_for_user(request.user)
    return render(
        request,
        "commission_blocked.html",
        {
            "base": base,
            "lang": lang,
            "record": record,
            "commission_rate_percent": int(COMMISSION_RATE * Decimal("100")),
        },
        status=403,
    )
