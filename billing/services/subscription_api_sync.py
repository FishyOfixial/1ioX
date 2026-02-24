import logging

from billing.services.one_nce_client import OneNCEClient

logger = logging.getLogger("billing.1nce")


def ensure_sim_enabled(subscription) -> bool:
    client = OneNCEClient()
    ok = client.enable_sim(subscription.sim.iccid)
    if not ok:
        logger.error(
            "Failed to enable SIM in 1NCE for subscription_id=%s iccid=%s",
            subscription.id,
            subscription.sim.iccid,
        )
    return ok


def ensure_sim_disabled(subscription) -> bool:
    client = OneNCEClient()
    ok = client.disable_sim(subscription.sim.iccid)
    if not ok:
        logger.error(
            "Failed to disable SIM in 1NCE for subscription_id=%s iccid=%s",
            subscription.id,
            subscription.sim.iccid,
        )
    return ok
