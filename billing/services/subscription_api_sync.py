import logging
import threading
import time

from django.conf import settings

from billing.services.one_nce_client import OneNCEClient
from auditlogs.utils import create_log

logger = logging.getLogger("billing.1nce")
_active_retry_keys: set[str] = set()
_active_retry_lock = threading.Lock()


def _retry_until_success(*, subscription_id: int, iccid: str, action_name: str, action_callable) -> bool:
    retry_delay = int(getattr(settings, "ONE_NCE_STATUS_SYNC_RETRY_DELAY_SECONDS", 20) or 20)
    max_retries = int(getattr(settings, "ONE_NCE_STATUS_SYNC_MAX_RETRIES", 5) or 5)
    attempt = 0

    while True:
        attempt += 1
        ok = action_callable()
        if ok:
            if attempt > 1:
                logger.info(
                    "Recovered 1NCE %s after retries. subscription_id=%s iccid=%s attempts=%s",
                    action_name,
                    subscription_id,
                    iccid,
                    attempt,
                )
                create_log(
                    log_type="SYSTEM",
                    severity="WARNING",
                    message=(
                        f"Recovered 1NCE {action_name} after retries "
                        f"(ICCID: {iccid})"
                    ),
                    reference_id=str(subscription_id),
                    metadata={"iccid": iccid, "attempts": attempt},
                )
            return True

        if attempt == 1 or attempt % 5 == 0:
            logger.warning(
                "1NCE %s failed. subscription_id=%s iccid=%s attempt=%s. Retrying in %ss",
                action_name,
                subscription_id,
                iccid,
                attempt,
                retry_delay,
            )
            create_log(
                log_type="SYSTEM",
                severity="ERROR",
                message=f"Failed to {action_name} SIM in 1NCE (ICCID: {iccid})",
                reference_id=str(subscription_id),
                metadata={"iccid": iccid, "attempt": attempt},
            )

        if max_retries > 0 and attempt >= max_retries:
            logger.error(
                "1NCE %s exhausted retries. subscription_id=%s iccid=%s attempts=%s",
                action_name,
                subscription_id,
                iccid,
                attempt,
            )
            return False

        time.sleep(retry_delay)


def _run_retry_thread(*, subscription_id: int, iccid: str, action_name: str, action_callable):
    retry_key = f"{action_name}:{iccid}"
    try:
        _retry_until_success(
            subscription_id=subscription_id,
            iccid=iccid,
            action_name=action_name,
            action_callable=action_callable,
        )
    finally:
        with _active_retry_lock:
            _active_retry_keys.discard(retry_key)


def _ensure_with_optional_background(*, subscription, action_name: str, action_callable) -> bool:
    subscription_id = int(subscription.id)
    iccid = str(subscription.sim.iccid)
    run_in_background = bool(getattr(settings, "ONE_NCE_STATUS_SYNC_RETRY_IN_BACKGROUND", True))

    if action_callable():
        return True

    retry_key = f"{action_name}:{iccid}"
    if run_in_background:
        with _active_retry_lock:
            if retry_key in _active_retry_keys:
                logger.info(
                    "1NCE %s retry already running in background. subscription_id=%s iccid=%s",
                    action_name,
                    subscription_id,
                    iccid,
                )
                return False
            _active_retry_keys.add(retry_key)

        thread = threading.Thread(
            target=_run_retry_thread,
            kwargs={
                "subscription_id": subscription_id,
                "iccid": iccid,
                "action_name": action_name,
                "action_callable": action_callable,
            },
            daemon=True,
            name=f"1nce_{action_name}_{iccid}",
        )
        thread.start()
        logger.warning(
            "1NCE %s failed on first attempt; background retry started. subscription_id=%s iccid=%s",
            action_name,
            subscription_id,
            iccid,
        )
        create_log(
            log_type="SYSTEM",
            severity="WARNING",
            message=f"Started background retries to {action_name} SIM in 1NCE (ICCID: {iccid})",
            reference_id=str(subscription_id),
            metadata={"iccid": iccid},
        )
        return False

    return _retry_until_success(
        subscription_id=subscription_id,
        iccid=iccid,
        action_name=action_name,
        action_callable=action_callable,
    )


def ensure_sim_enabled(subscription) -> bool:
    client = OneNCEClient()
    return _ensure_with_optional_background(
        subscription=subscription,
        action_name="enable",
        action_callable=lambda: client.enable_sim(subscription.sim.iccid),
    )


def ensure_sim_disabled(subscription) -> bool:
    client = OneNCEClient()
    return _ensure_with_optional_background(
        subscription=subscription,
        action_name="disable",
        action_callable=lambda: client.disable_sim(subscription.sim.iccid),
    )
