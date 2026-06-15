import logging
import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from auditlogs.utils import create_log
from billing.models import MercadoPagoOAuthState
from SIM_Control.models import Cliente, Distribuidor, Revendedor

logger = logging.getLogger("billing.mercadopago")

STATE_SESSION_KEY = "mercadopago_oauth_state"
STATE_MAX_AGE = timedelta(minutes=15)
TOKEN_REFRESH_MARGIN = timedelta(minutes=10)


class MercadoPagoOAuthError(Exception):
    pass


def _oauth_configured() -> bool:
    return bool(
        getattr(settings, "MERCADOPAGO_CLIENT_ID", "")
        and getattr(settings, "MERCADOPAGO_CLIENT_SECRET", "")
        and getattr(settings, "MERCADOPAGO_REDIRECT_URI", "")
    )


def build_authorization_url(*, request, profile) -> str:
    if not _oauth_configured():
        raise MercadoPagoOAuthError("Mercado Pago OAuth is not configured")

    state = secrets.token_urlsafe(32)
    profile_type = "distribuidor" if isinstance(profile, Distribuidor) else "revendedor"
    expires_at = timezone.now() + STATE_MAX_AGE
    MercadoPagoOAuthState.objects.create(
        state=state,
        user=request.user,
        profile_type=profile_type,
        profile_id=profile.id,
        expires_at=expires_at,
    )
    request.session[STATE_SESSION_KEY] = {
        "state": state,
        "profile_type": profile_type,
        "profile_id": profile.id,
        "created_at": timezone.now().isoformat(),
    }
    request.session.modified = True

    params = {
        "client_id": settings.MERCADOPAGO_CLIENT_ID,
        "response_type": "code",
        "platform_id": "mp",
        "redirect_uri": settings.MERCADOPAGO_REDIRECT_URI,
        "state": state,
    }
    return f"{settings.MERCADOPAGO_AUTH_URL}?{urlencode(params)}"


def _validate_session_state(request, received_state: str) -> dict[str, Any] | None:
    stored = request.session.pop(STATE_SESSION_KEY, None)
    request.session.modified = True
    if not stored or not received_state or stored.get("state") != received_state:
        return None

    try:
        created_at = datetime.fromisoformat(stored.get("created_at"))
        if timezone.is_naive(created_at):
            created_at = timezone.make_aware(created_at)
    except (TypeError, ValueError):
        raise MercadoPagoOAuthError("Invalid Mercado Pago OAuth state timestamp")

    if timezone.now() - created_at > STATE_MAX_AGE:
        raise MercadoPagoOAuthError("Expired Mercado Pago OAuth state")
    return stored


def _validate_persisted_state(request, received_state: str) -> dict[str, Any]:
    if not received_state:
        raise MercadoPagoOAuthError("Invalid Mercado Pago OAuth state")

    with transaction.atomic():
        state_record = (
            MercadoPagoOAuthState.objects.select_for_update()
            .filter(state=received_state, used_at__isnull=True)
            .first()
        )
        if not state_record:
            raise MercadoPagoOAuthError("Invalid Mercado Pago OAuth state")
        if state_record.user_id != request.user.id:
            raise MercadoPagoOAuthError("Mercado Pago OAuth state belongs to another user")
        if state_record.is_expired():
            raise MercadoPagoOAuthError("Expired Mercado Pago OAuth state")

        state_record.used_at = timezone.now()
        state_record.save(update_fields=["used_at"])

    return {
        "state": state_record.state,
        "profile_type": state_record.profile_type,
        "profile_id": state_record.profile_id,
        "created_at": state_record.created_at.isoformat(),
    }


def validate_state(*, request, received_state: str) -> dict[str, Any]:
    session_state = _validate_session_state(request, received_state)
    if session_state:
        MercadoPagoOAuthState.objects.filter(state=received_state, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        return session_state
    return _validate_persisted_state(request, received_state)


def get_profile_from_state(state_data: dict[str, Any]):
    profile_type = state_data.get("profile_type")
    profile_id = state_data.get("profile_id")
    if profile_type == "distribuidor":
        return Distribuidor.objects.get(id=profile_id)
    if profile_type == "revendedor":
        return Revendedor.objects.get(id=profile_id)
    raise MercadoPagoOAuthError("Invalid Mercado Pago OAuth profile")


def _token_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not _oauth_configured():
        raise MercadoPagoOAuthError("Mercado Pago OAuth is not configured")

    url = f"{settings.MERCADOPAGO_BASE_URL.rstrip('/')}/oauth/token"
    request_payload = {
        **payload,
        "client_id": settings.MERCADOPAGO_CLIENT_ID,
        "client_secret": settings.MERCADOPAGO_CLIENT_SECRET,
    }
    try:
        response = requests.post(url, json=request_payload, timeout=settings.MERCADOPAGO_TIMEOUT)
    except requests.RequestException as exc:
        logger.exception("mercadopago_oauth_request_failed")
        raise MercadoPagoOAuthError(str(exc)) from exc

    if not (200 <= response.status_code < 300):
        logger.error("mercadopago_oauth_token_failed status=%s body=%s", response.status_code, response.text)
        raise MercadoPagoOAuthError("Mercado Pago OAuth token exchange failed")

    try:
        return response.json()
    except ValueError as exc:
        raise MercadoPagoOAuthError("Mercado Pago OAuth returned invalid JSON") from exc


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    return _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.MERCADOPAGO_REDIRECT_URI,
        }
    )


def refresh_tokens(profile) -> bool:
    refresh_token = (profile.mercado_pago_refresh_token or "").strip()
    if not refresh_token:
        return False

    tokens = _token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})
    save_tokens(profile, tokens)
    logger.info("mercadopago_token_refreshed profile=%s profile_id=%s", profile.__class__.__name__, profile.id)
    return True


def save_tokens(profile, tokens: dict[str, Any]) -> None:
    expires_in = int(tokens.get("expires_in") or 0)
    profile.mercado_pago_user_id = str(tokens.get("user_id") or profile.mercado_pago_user_id or "")
    profile.mercado_pago_access_token = tokens.get("access_token") or profile.mercado_pago_access_token
    profile.mercado_pago_refresh_token = tokens.get("refresh_token") or profile.mercado_pago_refresh_token
    profile.mercado_pago_token_expires_at = timezone.now() + timedelta(seconds=expires_in) if expires_in else None
    profile.mercado_pago_connected_at = profile.mercado_pago_connected_at or timezone.now()
    profile.mercado_pago_is_connected = bool(profile.mercado_pago_access_token and profile.mercado_pago_refresh_token)
    profile.save(
        update_fields=[
            "mercado_pago_user_id",
            "mercado_pago_access_token",
            "mercado_pago_refresh_token",
            "mercado_pago_token_expires_at",
            "mercado_pago_connected_at",
            "mercado_pago_is_connected",
        ]
    )


def ensure_valid_access_token(profile) -> str | None:
    if not profile or not profile.mercado_pago_is_connected:
        return None

    expires_at = profile.mercado_pago_token_expires_at
    if expires_at and expires_at <= timezone.now() + TOKEN_REFRESH_MARGIN:
        try:
            refresh_tokens(profile)
        except MercadoPagoOAuthError:
            logger.exception(
                "mercadopago_token_refresh_failed profile=%s profile_id=%s",
                profile.__class__.__name__,
                profile.id,
            )
            create_log(
                log_type="BILLING",
                severity="ERROR",
                reference_id=str(profile.id),
                message="Mercado Pago token refresh failed",
                metadata={"profile": profile.__class__.__name__},
            )
            return None
    return (profile.mercado_pago_access_token or "").strip() or None


def get_connected_profile_for_user(user):
    cliente = Cliente.objects.filter(user=user).select_related("distribuidor", "revendedor").first()
    if not cliente:
        return None
    if cliente.revendedor and cliente.revendedor.mercado_pago_is_connected:
        return cliente.revendedor
    if cliente.distribuidor and cliente.distribuidor.mercado_pago_is_connected:
        return cliente.distribuidor
    if cliente.revendedor and cliente.revendedor.distribuidor and cliente.revendedor.distribuidor.mercado_pago_is_connected:
        return cliente.revendedor.distribuidor
    return None


def get_account_descriptor(profile) -> dict[str, Any]:
    if not profile:
        return {"type": None, "id": None, "user_id": None}
    account_type = "revendedor" if isinstance(profile, Revendedor) else "distribuidor"
    return {
        "type": account_type,
        "id": profile.id,
        "user_id": profile.mercado_pago_user_id,
    }


def get_profile_by_descriptor(account_type: str | None, account_id: int | None):
    if account_type == "revendedor" and account_id:
        return Revendedor.objects.filter(id=account_id).first()
    if account_type == "distribuidor" and account_id:
        return Distribuidor.objects.filter(id=account_id).first()
    return None
