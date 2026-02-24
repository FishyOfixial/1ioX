import logging
from decimal import Decimal
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.urls import reverse

from billing.models import MembershipPlan, Subscription, SubscriptionPurchase
from billing.services.mercadopago_client import MercadoPagoClient
from billing.services.subscription_api_sync import ensure_sim_enabled

logger = logging.getLogger("billing.mercadopago")


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


def create_checkout_for_plan(*, user, sim, plan: MembershipPlan, base_url: str, notification_url: str) -> Optional[str]:
    current_subscription = sim.current_subscription
    action = "renew" if current_subscription else "assign"

    purchase = SubscriptionPurchase.objects.create(
        user=user,
        sim=sim,
        plan=plan,
        action=action,
        amount=plan.price or Decimal("0"),
        currency="MXN",
        metadata={"sim_iccid": sim.iccid},
    )

    client = MercadoPagoClient()
    success_url = f"{base_url}{reverse('customer_portal:payment_success')}"
    failure_url = f"{base_url}{reverse('customer_portal:payment_failure')}"
    pending_url = f"{base_url}{reverse('customer_portal:payment_pending')}"

    configured_webhook = (getattr(settings, "MERCADOPAGO_WEBHOOK_URL", "") or "").strip()
    effective_notification_url = configured_webhook or notification_url

    payload = {
        "items": [
            {
                "title": f"Plan {plan.name} - SIM {sim.iccid}",
                "quantity": 1,
                "currency_id": "MXN",
                "unit_price": float(plan.price or 0),
            }
        ],
        "external_reference": str(purchase.reference),
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        "auto_return": "approved",
        "metadata": {
            "purchase_reference": str(purchase.reference),
            "sim_id": sim.id,
            "plan_id": plan.id,
            "action": action,
        },
    }

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
        return None

    purchase.mp_preference_id = response.get("id")
    purchase.metadata = {**purchase.metadata, "mp_preference_payload": response}
    purchase.save(update_fields=["mp_preference_id", "metadata", "updated_at"])

    return response.get("init_point") or response.get("sandbox_init_point")


def process_mercadopago_payment(payment_id: str) -> bool:
    client = MercadoPagoClient()
    payment = client.get_payment(payment_id)
    if not payment:
        return False

    reference = str(payment.get("external_reference") or "")
    if not reference:
        logger.error("MercadoPago payment without external_reference. payment_id=%s", payment_id)
        return False

    purchase = SubscriptionPurchase.objects.filter(reference=reference).select_related("sim", "plan").first()
    if not purchase:
        logger.error("MercadoPago purchase not found for reference=%s payment_id=%s", reference, payment_id)
        return False

    mp_status = str(payment.get("status") or "").lower()
    purchase.mp_payment_id = str(payment.get("id") or payment_id)
    purchase.mp_status = mp_status
    purchase.metadata = {**purchase.metadata, "payment_payload": payment}

    if mp_status == "approved":
        if purchase.status == "approved":
            purchase.save(update_fields=["mp_payment_id", "mp_status", "metadata", "updated_at"])
            return True

        with transaction.atomic():
            current_subscription = purchase.sim.current_subscription
            if current_subscription:
                current_subscription.extend(plan=purchase.plan)
                subscription = current_subscription
            else:
                subscription = Subscription.objects.create(
                    sim=purchase.sim,
                    plan=purchase.plan,
                    start_date=timezone.now(),
                    status="active",
                    auto_renew=False,
                )
                subscription.activate()

            ensure_sim_enabled(subscription)
            purchase.subscription = subscription
            purchase.status = "approved"
            purchase.save(
                update_fields=[
                    "subscription",
                    "status",
                    "mp_payment_id",
                    "mp_status",
                    "metadata",
                    "updated_at",
                ]
            )
        return True

    if mp_status in {"pending", "in_process"}:
        purchase.status = "pending"
    elif mp_status in {"cancelled", "rejected"}:
        purchase.status = "cancelled"
    else:
        purchase.status = "failed"

    purchase.save(update_fields=["status", "mp_payment_id", "mp_status", "metadata", "updated_at"])
    return True
