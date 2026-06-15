import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from auditlogs.utils import create_log
from billing.models import DistributorSale
from billing.services.mercadopago_oauth import (
    MercadoPagoOAuthError,
    build_authorization_url,
    exchange_code_for_tokens,
    get_profile_from_state,
    save_tokens,
    validate_state,
)
from SIM_Control.decorators import user_in
from SIM_Control.models import Distribuidor, Revendedor
from SIM_Control.my_views.translations import get_translation

logger = logging.getLogger("billing.mercadopago")


def _current_profile(user):
    if user.user_type == "DISTRIBUIDOR":
        return Distribuidor.objects.filter(user=user).first()
    if user.user_type == "REVENDEDOR":
        return Revendedor.objects.filter(user=user).first()
    return None


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
    lang, base = get_translation(request.user, "dashboard")
    today = timezone.localdate()
    month = request.GET.get("month") or f"{today.month:02d}"
    year = request.GET.get("year") or str(today.year)
    period = f"{year}-{str(month).zfill(2)}"

    sales = DistributorSale.objects.select_related("distribuidor", "revendedor", "cliente", "plan").filter(period=period)
    profile = _current_profile(request.user)
    if request.user.user_type == "DISTRIBUIDOR" and profile:
        sales = sales.filter(distribuidor=profile)
    elif request.user.user_type == "REVENDEDOR" and profile:
        sales = sales.filter(revendedor=profile)

    total = sales.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    current_profile = _current_profile(request.user)
    return render(
        request,
        "mercadopago_report.html",
        {
            "base": base,
            "lang": lang,
            "sales": sales.order_by("-paid_at"),
            "total": total,
            "period": period,
            "selected_month": str(month).zfill(2),
            "selected_year": year,
            "months": [f"{number:02d}" for number in range(1, 13)],
            "years": [str(today.year + offset) for offset in range(-2, 2)],
            "mercado_pago_profile": current_profile,
        },
    )
