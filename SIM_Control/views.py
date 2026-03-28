import logging
import threading

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

from auditlogs.utils import create_log
from services.external_api import get_cron_override

from .security import get_default_post_login_redirect, get_safe_referer_redirect
from .utils import log_security_event
from .my_views import (
    adm_,
    agsl_,
    as_,
    cc_,
    cd_,
    co_,
    cr_,
    ds_,
    gl_,
    gs_,
    gsd_,
    gu_,
    liv_,
    lov_,
    od_,
    rdq_,
    rm_,
    ro_,
    rsim_,
    rsms_,
    rsq_,
    rsta_,
    sd_,
    ss_,
    ud_,
    usl_,
    uss_,
    uu_,
    uua_,
)

logger = logging.getLogger(__name__)


def _is_authorized_cron(request):
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {settings.CRON_TOKEN}"


@csrf_exempt
def cron_usage(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not _is_authorized_cron(request):
        log_security_event(
            "Unauthorized cron usage request",
            metadata={"path": request.path},
        )
        return JsonResponse({"error": "Unauthorized"}, status=401)

    override = get_cron_override({"task": "cron_usage", "method": request.method})
    if isinstance(override, dict):
        logger.info("Local cron override active for cron_usage")
        return JsonResponse(override.get("body", {"status": "accepted"}), status=int(override.get("status", 202)))

    def worker():
        try:
            logger.info("Background: starting usage update")
            call_command("actual_usage")
            call_command("update_data_quotas")
            call_command("update_sms_quotas")
            logger.info("Background: usage update finished")
        except Exception:
            logger.exception("Background usage update failed")
            create_log(log_type="SYSTEM", severity="ERROR", message="Background usage update failed")

    thread = threading.Thread(target=worker, daemon=True, name="cron_usage_worker")
    thread.start()
    return JsonResponse({"status": "accepted"}, status=202)


@csrf_exempt
def cron_status(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not _is_authorized_cron(request):
        log_security_event(
            "Unauthorized cron status request",
            metadata={"path": request.path},
        )
        return JsonResponse({"error": "Unauthorized"}, status=401)

    override = get_cron_override({"task": "cron_status", "method": request.method})
    if isinstance(override, dict):
        logger.info("Local cron override active for cron_status")
        return JsonResponse(override.get("body", {"status": "accepted"}), status=int(override.get("status", 202)))

    def worker():
        try:
            logger.info("Background: starting update_status")
            call_command("update_status")
            call_command("update_sims")
            logger.info("Background: update_status finished")
        except Exception:
            logger.exception("Background update_status failed")
            create_log(log_type="SYSTEM", severity="ERROR", message="Background status update failed")

    thread = threading.Thread(target=worker, daemon=True, name="cron_status_worker")
    thread.start()
    return JsonResponse({"status": "accepted"}, status=202)


@csrf_exempt
def cron_check_subscriptions(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not _is_authorized_cron(request):
        log_security_event(
            "Unauthorized cron subscription check request",
            metadata={"path": request.path},
        )
        return JsonResponse({"error": "Unauthorized"}, status=401)

    override = get_cron_override({"task": "cron_check_subscriptions", "method": request.method})
    if isinstance(override, dict):
        logger.info("Local cron override active for cron_check_subscriptions")
        return JsonResponse(override.get("body", {"status": "accepted"}), status=int(override.get("status", 202)))

    def worker():
        try:
            logger.info("Background: starting check_subscriptions")
            call_command("check_subscriptions")
            logger.info("Background: check_subscriptions finished")
        except Exception:
            logger.exception("Background check_subscriptions failed")
            create_log(log_type="SYSTEM", severity="ERROR", message="Background check_subscriptions failed")

    thread = threading.Thread(target=worker, daemon=True, name="cron_check_subscriptions_worker")
    thread.start()
    return JsonResponse({"status": "accepted"}, status=202)


@login_required
def set_language(request, lang):
    if lang not in {"es", "en", "pt"}:
        log_security_event(
            "Invalid language selection rejected",
            user=request.user,
            metadata={"lang": lang, "path": request.path},
        )
        return redirect(get_default_post_login_redirect(request.user))

    request.user.preferred_lang = lang
    request.user.save()
    fallback_url = get_default_post_login_redirect(request.user)
    return redirect(get_safe_referer_redirect(request, fallback_url))


def role_based_404_redirect(request, exception):
    if request.user.is_authenticated:
        if request.user.user_type == "CLIENTE":
            return redirect("customer_portal:dashboard")
        return redirect("dashboard")
    return redirect("login")


@login_required
def root_entrypoint(request):
    if request.user.user_type == "CLIENTE":
        return redirect("customer_portal:dashboard")
    return ds_(request)
