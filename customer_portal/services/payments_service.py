import logging
import uuid
from decimal import Decimal
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.urls import reverse

from auditlogs.utils import create_log
from billing.models import DistributorSale, MembershipPlan, Subscription, SubscriptionPurchase
from billing.pricing import resolve_plan_price_for_user
from billing.services.mercadopago_client import MercadoPagoClient
from billing.services.mercadopago_oauth import (
    ensure_valid_access_token,
    get_account_descriptor,
    get_connected_profile_for_user,
    get_profile_by_descriptor,
)
from billing.services.subscription_api_sync import ensure_sim_enabled
from SIM_Control.models import Cliente, Distribuidor, Revendedor

logger = logging.getLogger("billing.mercadopago")


def _is_prepago_subscription(subscription: Subscription | None) -> bool:
    if not subscription or not subscription.plan:
        return False
    return int(subscription.plan.duration_days or 0) == 1825


def _is_valid_public_callback_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"}:
            return False
        if not parsed.netloc:
            return False
        host = (parsed.hostname or "").lower()
        if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
            return False
        return True
    except Exception:
        return False


def _append_webhook_token(url: str) -> str:
    webhook_token = (getattr(settings, "MERCADOPAGO_WEBHOOK_TOKEN", "") or "").strip()
    if not webhook_token or not url:
        return url

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if query.get("token"):
        return url

    query["token"] = webhook_token
    return urlunparse(parsed._replace(query=urlencode(query)))


def _resolve_notification_url(notification_url: str) -> str:
    configured_webhook = (getattr(settings, "MERCADOPAGO_WEBHOOK_URL", "") or "").strip()
    return _append_webhook_token(configured_webhook or notification_url)


def _resolve_plan_period_for_recurring(plan: MembershipPlan) -> tuple[int, str]:
    unit = (plan.period_unit or "").lower()
    count = int(plan.period_count or 0)
    if count > 0 and unit in {"day", "month", "year"}:
        if unit == "year":
            return count * 12, "months"
        if unit == "month":
            return count, "months"
        return count, "days"

    duration_days = int(plan.duration_days or 0)
    if duration_days in {30, 90, 180, 365, 1825}:
        mapping = {
            30: (1, "months"),
            90: (3, "months"),
            180: (6, "months"),
            365: (12, "months"),
            1825: (60, "months"),
        }
        return mapping[duration_days]
    if duration_days > 0:
        return duration_days, "days"
    return 1, "months"


def _build_checkout_payload(
    *,
    external_reference: str,
    base_url: str,
    metadata: dict,
    items: list[dict],
) -> dict:
    success_url = f"{base_url}{reverse('customer_portal:payment_success')}"
    failure_url = f"{base_url}{reverse('customer_portal:payment_failure')}"
    pending_url = f"{base_url}{reverse('customer_portal:payment_pending')}"
    return {
        "items": items,
        "external_reference": external_reference,
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        "auto_return": "approved",
        "metadata": metadata,
    }


def _get_checkout_client_for_user(user) -> tuple[MercadoPagoClient, dict]:
    profile = get_connected_profile_for_user(user)
    access_token = ensure_valid_access_token(profile) if profile else None
    if access_token:
        return MercadoPagoClient(access_token=access_token), get_account_descriptor(profile)
    return MercadoPagoClient(), get_account_descriptor(None)


def _get_payment_client_for_purchase(purchase: SubscriptionPurchase | None) -> MercadoPagoClient:
    if not purchase:
        return MercadoPagoClient()
    profile = get_profile_by_descriptor(purchase.mp_account_type, purchase.mp_account_id)
    access_token = ensure_valid_access_token(profile) if profile else None
    return MercadoPagoClient(access_token=access_token) if access_token else MercadoPagoClient()


def _candidate_profiles_for_payment(account_user_id: str | None = None):
    if account_user_id:
        profile = Revendedor.objects.filter(
            mercado_pago_is_connected=True,
            mercado_pago_user_id=str(account_user_id),
        ).first()
        if profile:
            return [profile]
        profile = Distribuidor.objects.filter(
            mercado_pago_is_connected=True,
            mercado_pago_user_id=str(account_user_id),
        ).first()
        if profile:
            return [profile]

    return list(Revendedor.objects.filter(mercado_pago_is_connected=True)) + list(
        Distribuidor.objects.filter(mercado_pago_is_connected=True)
    )


def _get_payment_with_correct_token(payment_id: str, account_user_id: str | None = None) -> Optional[dict]:
    for profile in _candidate_profiles_for_payment(account_user_id):
        access_token = ensure_valid_access_token(profile)
        if not access_token:
            continue
        payment = MercadoPagoClient(access_token=access_token).get_payment(payment_id)
        if payment:
            return payment
    return MercadoPagoClient().get_payment(payment_id)


def _get_preapproval_with_correct_token(preapproval_id: str, account_user_id: str | None = None) -> Optional[dict]:
    for profile in _candidate_profiles_for_payment(account_user_id):
        access_token = ensure_valid_access_token(profile)
        if not access_token:
            continue
        preapproval = MercadoPagoClient(access_token=access_token).get_preapproval(preapproval_id)
        if preapproval:
            return preapproval
    return MercadoPagoClient().get_preapproval(preapproval_id)


def _parse_mp_datetime(value: str | None):
    parsed = parse_datetime(value) if value else None
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _get_sale_participants(user):
    cliente = Cliente.objects.filter(user=user).select_related("distribuidor", "revendedor__distribuidor").first()
    if not cliente:
        return None, None, None
    distribuidor = cliente.distribuidor or (cliente.revendedor.distribuidor if cliente.revendedor else None)
    return cliente, distribuidor, cliente.revendedor


def _record_distributor_sale(current_purchase: SubscriptionPurchase, payment: dict, status: str) -> None:
    payment_id = str(payment.get("id") or current_purchase.mp_payment_id or "")
    if not payment_id:
        return

    paid_at = (
        _parse_mp_datetime(payment.get("date_approved"))
        or _parse_mp_datetime(payment.get("date_created"))
        or timezone.now()
    )
    cliente, distribuidor, revendedor = _get_sale_participants(current_purchase.user)
    DistributorSale.objects.update_or_create(
        purchase=current_purchase,
        defaults={
            "distribuidor": distribuidor,
            "revendedor": revendedor,
            "cliente": cliente,
            "plan": current_purchase.plan,
            "amount": current_purchase.amount,
            "currency": current_purchase.currency,
            "payment_id": payment_id,
            "paid_at": paid_at,
            "status": status,
            "period": paid_at.strftime("%Y-%m"),
        },
    )


def create_checkout_for_plan(*, user, sim, plan: MembershipPlan, base_url: str, notification_url: str) -> Optional[str]:
    current_subscription = sim.current_subscription
    action = "renew" if current_subscription else "assign"
    effective_price, override = resolve_plan_price_for_user(user=user, plan=plan)
    client, account = _get_checkout_client_for_user(user)

    purchase = SubscriptionPurchase.objects.create(
        user=user,
        sim=sim,
        plan=plan,
        action=action,
        amount=effective_price,
        currency="MXN",
        metadata={
            "sim_iccid": sim.iccid,
            "base_price": str(plan.price or Decimal("0")),
            "effective_price": str(effective_price),
            "adjustment_percent": str(getattr(override, "adjustment_percent", Decimal("0"))),
            "mp_account_type": account["type"],
            "mp_account_id": account["id"],
            "mp_account_user_id": account["user_id"],
        },
        mp_account_type=account["type"],
        mp_account_id=account["id"],
        mp_account_user_id=account["user_id"],
    )

    effective_notification_url = _resolve_notification_url(notification_url)

    payload = _build_checkout_payload(
        external_reference=str(purchase.reference),
        base_url=base_url,
        metadata={
            "purchase_reference": str(purchase.reference),
            "sim_id": sim.id,
            "plan_id": plan.id,
            "action": action,
            "is_bulk": False,
        },
        items=[
            {
                "title": f"Plan {plan.name} - SIM {sim.iccid}",
                "quantity": 1,
                "currency_id": "MXN",
                "unit_price": float(effective_price),
            }
        ],
    )

    if _is_valid_public_callback_url(effective_notification_url):
        payload["notification_url"] = effective_notification_url
    else:
        logger.warning(
            "MercadoPago notification_url omitted (invalid/non-public): %s",
            effective_notification_url,
        )

    response = client.create_preference(payload)
    if not response:
        purchase.status = "failed"
        purchase.save(update_fields=["status", "updated_at"])
        create_log(
            log_type="BILLING",
            severity="ERROR",
            user=user,
            reference_id=str(purchase.reference),
            message="Payment checkout creation failed",
            metadata={"sim_iccid": sim.iccid, "plan": plan.name, "amount": str(purchase.amount)},
        )
        logger.error(
            "payment_checkout_failed sim=%s reference=%s amount=%s plan=%s",
            sim.iccid,
            purchase.reference,
            purchase.amount,
            plan.name,
        )
        return None

    purchase.mp_preference_id = response.get("id")
    purchase.metadata = {**purchase.metadata, "mp_preference_payload": response}
    purchase.save(update_fields=["mp_preference_id", "metadata", "updated_at"])
    logger.info(
        "payment_checkout_created sim=%s reference=%s preference_id=%s plan=%s amount=%s notification_url_configured=%s",
        sim.iccid,
        purchase.reference,
        purchase.mp_preference_id,
        plan.name,
        purchase.amount,
        bool(payload.get("notification_url")),
    )

    return response.get("init_point") or response.get("sandbox_init_point")


def create_checkout_for_bulk_plan(
    *,
    user,
    sims,
    plan: MembershipPlan,
    base_url: str,
    notification_url: str,
) -> Optional[str]:
    sims = list(sims)
    if not sims:
        return None
    effective_price, override = resolve_plan_price_for_user(user=user, plan=plan)
    client, account = _get_checkout_client_for_user(user)

    batch_reference = str(uuid.uuid4())
    purchases = []
    for sim in sims:
        current_subscription = sim.current_subscription
        action = "renew" if current_subscription else "assign"
        purchases.append(
            SubscriptionPurchase(
                user=user,
                sim=sim,
                plan=plan,
                action=action,
                amount=effective_price,
                currency="MXN",
                metadata={
                    "sim_iccid": sim.iccid,
                    "batch_reference": batch_reference,
                    "is_bulk": True,
                    "base_price": str(plan.price or Decimal("0")),
                    "effective_price": str(effective_price),
                    "adjustment_percent": str(getattr(override, "adjustment_percent", Decimal("0"))),
                    "mp_account_type": account["type"],
                    "mp_account_id": account["id"],
                    "mp_account_user_id": account["user_id"],
                },
                mp_account_type=account["type"],
                mp_account_id=account["id"],
                mp_account_user_id=account["user_id"],
            )
        )

    references = [purchase.reference for purchase in purchases]
    SubscriptionPurchase.objects.bulk_create(purchases)
    purchases = list(
        SubscriptionPurchase.objects.filter(reference__in=references).select_related("sim", "plan")
    )
    if not purchases:
        return None

    purchase_references = [str(purchase.reference) for purchase in purchases]
    lead_purchase = purchases[0]
    lead_purchase.metadata = {
        **lead_purchase.metadata,
        "batch_purchase_references": purchase_references,
    }
    lead_purchase.save(update_fields=["metadata", "updated_at"])

    effective_notification_url = _resolve_notification_url(notification_url)

    payload = _build_checkout_payload(
        external_reference=str(lead_purchase.reference),
        base_url=base_url,
        metadata={
            "purchase_reference": str(lead_purchase.reference),
            "batch_reference": batch_reference,
            "batch_purchase_references": purchase_references,
            "sim_ids": [purchase.sim_id for purchase in purchases],
            "plan_id": plan.id,
            "is_bulk": True,
        },
        items=[
            {
                "title": f"Plan {plan.name} - SIM {current_purchase.sim.iccid}",
                "quantity": 1,
                "currency_id": "MXN",
                "unit_price": float(current_purchase.amount or 0),
            }
            for current_purchase in purchases
        ],
    )

    if _is_valid_public_callback_url(effective_notification_url):
        payload["notification_url"] = effective_notification_url
    else:
        logger.warning(
            "MercadoPago notification_url omitted (invalid/non-public): %s",
            effective_notification_url,
        )

    response = client.create_preference(payload)
    if not response:
        SubscriptionPurchase.objects.filter(id__in=[purchase.id for purchase in purchases]).update(status="failed")
        create_log(
            log_type="BILLING",
            severity="ERROR",
            user=user,
            reference_id=batch_reference,
            message="Bulk payment checkout creation failed",
            metadata={
                "sims": [purchase.sim.iccid for purchase in purchases],
                "plan": plan.name,
            },
        )
        logger.error(
            "payment_checkout_failed_bulk user=%s sims=%s amount=%s plan=%s",
            user.id,
            ",".join(purchase.sim.iccid for purchase in purchases),
            sum((purchase.amount for purchase in purchases), Decimal("0")),
            plan.name,
        )
        return None

    preference_id = response.get("id")
    for purchase in purchases:
        purchase.mp_preference_id = preference_id
        purchase.metadata = {**purchase.metadata, "mp_preference_payload": response}
    SubscriptionPurchase.objects.bulk_update(purchases, ["mp_preference_id", "metadata", "updated_at"])
    logger.info(
        "payment_checkout_created_bulk user=%s references=%s preference_id=%s plan=%s sims=%s notification_url_configured=%s",
        user.id,
        ",".join(purchase_references),
        preference_id,
        plan.name,
        ",".join(purchase.sim.iccid for purchase in purchases),
        bool(payload.get("notification_url")),
    )

    return response.get("init_point") or response.get("sandbox_init_point")


def create_auto_renew_checkout_for_subscription(
    *,
    user,
    subscription: Subscription,
    base_url: str,
    notification_url: str,
) -> Optional[str]:
    if not getattr(settings, "MERCADOPAGO_SUBSCRIPTIONS_ENABLED", False):
        logger.warning(
            "auto_renew_setup_skipped subscriptions integration disabled. sim=%s subscription_id=%s",
            subscription.sim.iccid,
            subscription.id,
        )
        return None

    plan = subscription.plan
    effective_price, override = resolve_plan_price_for_user(user=user, plan=plan)
    if effective_price <= 0:
        logger.warning(
            "auto_renew_setup_skipped invalid recurring amount. sim=%s subscription_id=%s plan=%s amount=%s",
            subscription.sim.iccid,
            subscription.id,
            plan.name,
            effective_price,
        )
        return None

    current_subscription = subscription
    frequency, frequency_type = _resolve_plan_period_for_recurring(plan)
    client, account = _get_checkout_client_for_user(user)

    purchase = SubscriptionPurchase.objects.create(
        user=user,
        sim=current_subscription.sim,
        plan=plan,
        action="renew",
        status="created",
        amount=effective_price,
        currency="MXN",
        subscription=current_subscription,
        metadata={
            "sim_iccid": current_subscription.sim.iccid,
            "is_auto_renew_setup": True,
            "base_price": str(plan.price or Decimal("0")),
            "effective_price": str(effective_price),
            "adjustment_percent": str(getattr(override, "adjustment_percent", Decimal("0"))),
            "mp_account_type": account["type"],
            "mp_account_id": account["id"],
            "mp_account_user_id": account["user_id"],
        },
        mp_account_type=account["type"],
        mp_account_id=account["id"],
        mp_account_user_id=account["user_id"],
    )

    effective_notification_url = _resolve_notification_url(notification_url)
    success_url = f"{base_url}{reverse('customer_portal:payment_success')}"
    reason_prefix = (getattr(settings, "MERCADOPAGO_SUBSCRIPTION_REASON_PREFIX", "") or "Auto renew").strip()
    payload = {
        "reason": f"{reason_prefix} - SIM {current_subscription.sim.iccid} - {plan.name}",
        "external_reference": str(purchase.reference),
        "payer_email": (user.email or "").strip(),
        "back_url": success_url,
        "status": "pending",
        "auto_recurring": {
            "frequency": frequency,
            "frequency_type": frequency_type,
            "transaction_amount": float(effective_price),
            "currency_id": "MXN",
        },
    }
    if not payload["payer_email"]:
        logger.error(
            "auto_renew_setup_failed missing payer email. user_id=%s sim=%s subscription_id=%s",
            user.id,
            current_subscription.sim.iccid,
            current_subscription.id,
        )
        return None
    if _is_valid_public_callback_url(effective_notification_url):
        payload["notification_url"] = effective_notification_url

    response = client.create_preapproval(payload)
    if not response:
        purchase.status = "failed"
        purchase.save(update_fields=["status", "updated_at"])
        create_log(
            log_type="BILLING",
            severity="ERROR",
            user=user,
            reference_id=str(purchase.reference),
            message="Auto-renew setup failed",
            metadata={"sim_iccid": current_subscription.sim.iccid, "plan": plan.name},
        )
        logger.error(
            "auto_renew_setup_failed sim=%s reference=%s plan=%s",
            current_subscription.sim.iccid,
            purchase.reference,
            plan.name,
        )
        return None

    preapproval_id = str(response.get("id") or "")
    preapproval_status = str(response.get("status") or "")
    # Do not enable auto-renew until webhook confirms authorization.
    current_subscription.auto_renew = False
    current_subscription.mp_preapproval_id = preapproval_id or current_subscription.mp_preapproval_id
    current_subscription.mp_preapproval_status = preapproval_status or current_subscription.mp_preapproval_status
    current_subscription.mp_last_event_at = timezone.now()
    current_subscription.save(
        update_fields=[
            "auto_renew",
            "mp_preapproval_id",
            "mp_preapproval_status",
            "mp_last_event_at",
        ]
    )

    purchase.status = "pending"
    purchase.mp_status = preapproval_status or "pending"
    purchase.mp_preference_id = preapproval_id or None
    purchase.metadata = {
        **purchase.metadata,
        "mp_preapproval_payload": response,
        "is_auto_renew_setup": True,
    }
    purchase.save(update_fields=["status", "mp_status", "mp_preference_id", "metadata", "updated_at"])

    return response.get("init_point")


def disable_subscription_auto_renew(subscription: Subscription) -> bool:
    preapproval_id = (subscription.mp_preapproval_id or "").strip()
    if preapproval_id:
        purchase = SubscriptionPurchase.objects.filter(subscription=subscription).order_by("-created_at").first()
        client = _get_payment_client_for_purchase(purchase)
        if not client.cancel_preapproval(preapproval_id):
            logger.error(
                "auto_renew_disable_failed subscription_id=%s sim=%s preapproval_id=%s",
                subscription.id,
                subscription.sim.iccid,
                preapproval_id,
            )
            return False

    subscription.auto_renew = False
    subscription.mp_preapproval_status = "cancelled"
    subscription.mp_last_event_at = timezone.now()
    subscription.save(update_fields=["auto_renew", "mp_preapproval_status", "mp_last_event_at"])
    logger.info(
        "auto_renew_disabled subscription_id=%s sim=%s preapproval_id=%s",
        subscription.id,
        subscription.sim.iccid,
        preapproval_id,
    )
    create_log(
        log_type="BILLING",
        severity="INFO",
        reference_id=str(subscription.id),
        message="Auto-renew disabled",
        metadata={"sim_iccid": subscription.sim.iccid, "preapproval_id": preapproval_id},
    )
    return True


def process_mercadopago_preapproval(preapproval_id: str, account_user_id: str | None = None) -> bool:
    preapproval = _get_preapproval_with_correct_token(preapproval_id, account_user_id=account_user_id)
    if not preapproval:
        create_log(
            log_type="BILLING",
            severity="ERROR",
            reference_id=preapproval_id,
            message="Mercado Pago preapproval fetch failed",
        )
        return False

    external_reference = str(preapproval.get("external_reference") or "")
    preapproval_status = str(preapproval.get("status") or "").lower()
    if not external_reference:
        logger.error("preapproval without external_reference. preapproval_id=%s", preapproval_id)
        return False

    purchase = SubscriptionPurchase.objects.filter(reference=external_reference).select_related("subscription", "sim").first()
    if not purchase:
        logger.error(
            "preapproval purchase not found reference=%s preapproval_id=%s",
            external_reference,
            preapproval_id,
        )
        return False

    subscription = purchase.subscription or purchase.sim.current_subscription
    if not subscription:
        logger.error(
            "preapproval without subscription reference=%s preapproval_id=%s",
            external_reference,
            preapproval_id,
        )
        return False

    subscription.mp_preapproval_id = preapproval_id
    subscription.mp_preapproval_status = preapproval_status
    subscription.mp_last_event_at = timezone.now()
    subscription.auto_renew = preapproval_status == "authorized"
    subscription.save(
        update_fields=[
            "mp_preapproval_id",
            "mp_preapproval_status",
            "mp_last_event_at",
            "auto_renew",
        ]
    )

    purchase.mp_status = preapproval_status
    purchase.metadata = {**purchase.metadata, "mp_preapproval_payload": preapproval}
    if preapproval_status == "authorized":
        purchase.status = "approved"
    elif preapproval_status == "pending":
        purchase.status = "pending"
    elif preapproval_status in {"cancelled", "paused"}:
        purchase.status = "cancelled"
    else:
        purchase.status = "failed"
    purchase.save(update_fields=["status", "mp_status", "metadata", "updated_at"])

    logger.info(
        "preapproval_updated sim=%s subscription_id=%s preapproval_id=%s status=%s",
        subscription.sim.iccid,
        subscription.id,
        preapproval_id,
        preapproval_status,
    )
    create_log(
        log_type="BILLING",
        severity="INFO",
        reference_id=str(subscription.id),
        message="Mercado Pago preapproval processed",
        metadata={
            "sim_iccid": subscription.sim.iccid,
            "preapproval_id": preapproval_id,
            "status": preapproval_status,
        },
    )
    return True


def process_mercadopago_payment(payment_id: str, account_user_id: str | None = None) -> bool:
    payment = _get_payment_with_correct_token(payment_id, account_user_id=account_user_id)
    if not payment:
        create_log(
            log_type="BILLING",
            severity="ERROR",
            reference_id=payment_id,
            message="Mercado Pago payment fetch failed",
        )
        return False

    reference = str(payment.get("external_reference") or "")
    if not reference:
        logger.error("MercadoPago payment without external_reference. payment_id=%s", payment_id)
        create_log(
            log_type="BILLING",
            severity="ERROR",
            reference_id=payment_id,
            message="Mercado Pago payment without external reference",
        )
        return False

    purchase = SubscriptionPurchase.objects.filter(reference=reference).select_related("sim", "plan").first()
    if not purchase:
        logger.error("MercadoPago purchase not found for reference=%s payment_id=%s", reference, payment_id)
        create_log(
            log_type="BILLING",
            severity="ERROR",
            reference_id=reference,
            message="Mercado Pago purchase not found",
            metadata={"payment_id": payment_id},
        )
        return False

    account_payment = _get_payment_client_for_purchase(purchase).get_payment(payment_id)
    if account_payment:
        payment = account_payment

    related_references = purchase.metadata.get("batch_purchase_references")
    if isinstance(related_references, list) and related_references:
        purchases = list(
            SubscriptionPurchase.objects.filter(reference__in=related_references).select_related("sim", "plan")
        )
    else:
        purchases = [purchase]

    mp_status = str(payment.get("status") or "").lower()
    mp_payment_id = str(payment.get("id") or payment_id)

    if mp_status == "approved":
        if all(p.status == "approved" for p in purchases):
            for current_purchase in purchases:
                current_purchase.mp_payment_id = mp_payment_id
                current_purchase.mp_status = mp_status
                current_purchase.metadata = {**current_purchase.metadata, "payment_payload": payment}
                _record_distributor_sale(current_purchase, payment, "approved")
                _record_distributor_sale(current_purchase, payment, "approved")
            SubscriptionPurchase.objects.bulk_update(
                purchases,
                ["mp_payment_id", "mp_status", "metadata", "updated_at"],
            )
            logger.info(
                "payment_already_applied sims=%s payment_id=%s reference=%s amount=%s status=%s",
                ",".join(current_purchase.sim.iccid for current_purchase in purchases),
                mp_payment_id,
                reference,
                sum((current_purchase.amount for current_purchase in purchases), Decimal("0")),
                mp_status,
            )
            create_log(
                log_type="BILLING",
                severity="INFO",
                reference_id=reference,
                message="Payment already applied",
                metadata={"payment_id": mp_payment_id, "status": mp_status},
            )
            return True

        with transaction.atomic():
            for current_purchase in purchases:
                current_subscription = current_purchase.sim.current_subscription
                if current_subscription:
                    if _is_prepago_subscription(current_subscription):
                        current_subscription.overwrite_plan(current_purchase.plan)
                    else:
                        current_subscription.extend(plan=current_purchase.plan)
                    subscription = current_subscription
                else:
                    subscription = Subscription.objects.create(
                        sim=current_purchase.sim,
                        plan=current_purchase.plan,
                        start_date=timezone.now(),
                        status="active",
                        auto_renew=False,
                    )
                    subscription.activate()

                ensure_sim_enabled(subscription)
                current_purchase.subscription = subscription
                current_purchase.status = "approved"
                current_purchase.mp_payment_id = mp_payment_id
                current_purchase.mp_status = mp_status
                current_purchase.metadata = {**current_purchase.metadata, "payment_payload": payment}

            SubscriptionPurchase.objects.bulk_update(
                purchases,
                [
                    "subscription",
                    "status",
                    "mp_payment_id",
                    "mp_status",
                    "metadata",
                    "updated_at",
                ],
            )

        logger.info(
            "payment_approved sims=%s payment_id=%s reference=%s amount=%s status=%s",
            ",".join(current_purchase.sim.iccid for current_purchase in purchases),
            mp_payment_id,
            reference,
            sum((current_purchase.amount for current_purchase in purchases), Decimal("0")),
            mp_status,
        )
        create_log(
            log_type="BILLING",
            severity="INFO",
            reference_id=reference,
            message="Payment applied",
            metadata={
                "payment_id": mp_payment_id,
                "status": mp_status,
                "sims": [current_purchase.sim.iccid for current_purchase in purchases],
            },
        )
        return True

    if mp_status in {"pending", "in_process"}:
        purchase_status = "pending"
    elif mp_status in {"cancelled", "rejected"}:
        purchase_status = "cancelled"
    else:
        purchase_status = "failed"

    for current_purchase in purchases:
        current_purchase.status = purchase_status
        current_purchase.mp_payment_id = mp_payment_id
        current_purchase.mp_status = mp_status
        current_purchase.metadata = {**current_purchase.metadata, "payment_payload": payment}
        _record_distributor_sale(current_purchase, payment, purchase_status)

    SubscriptionPurchase.objects.bulk_update(
        purchases,
        ["status", "mp_payment_id", "mp_status", "metadata", "updated_at"],
    )
    logger.info(
        "payment_not_approved sims=%s payment_id=%s reference=%s amount=%s status=%s purchase_status=%s",
        ",".join(current_purchase.sim.iccid for current_purchase in purchases),
        mp_payment_id,
        reference,
        sum((current_purchase.amount for current_purchase in purchases), Decimal("0")),
        mp_status,
        purchase_status,
    )
    create_log(
        log_type="BILLING",
        severity="WARNING" if purchase_status in {"pending", "cancelled"} else "ERROR",
        reference_id=reference,
        message="Payment not approved",
        metadata={
            "payment_id": mp_payment_id,
            "status": mp_status,
            "purchase_status": purchase_status,
            "sims": [current_purchase.sim.iccid for current_purchase in purchases],
        },
    )
    return True
