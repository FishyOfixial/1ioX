import hashlib
import time
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from auditlogs.utils import create_log


def get_client_ip(request):
    forwarded_for = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return (request.META.get("REMOTE_ADDR") or "").strip() or "unknown"


def _cache_key(prefix, value):
    digest = hashlib.sha256((value or "").encode("utf-8")).hexdigest()
    return f"security:{prefix}:{digest}"


def _increment_counter(key, timeout):
    if cache.add(key, 1, timeout):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout)
        return 1


def _build_lockout_state(username, client_ip):
    now = time.time()
    user_blocked_until = cache.get(_cache_key("login_block_user", username), 0) or 0
    ip_blocked_until = cache.get(_cache_key("login_block_ip", client_ip), 0) or 0
    blocked_until = max(user_blocked_until, ip_blocked_until)
    if blocked_until <= now:
        return None

    return {
        "blocked_until": blocked_until,
        "retry_after_seconds": max(int(blocked_until - now), 1),
    }


def get_login_lockout_state(request, username):
    normalized_username = (username or "").strip().lower()
    return _build_lockout_state(normalized_username, get_client_ip(request))


def register_login_failure(request, username):
    normalized_username = (username or "").strip().lower()
    client_ip = get_client_ip(request)
    window = int(getattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 900) or 900)
    max_attempts = int(getattr(settings, "LOGIN_RATE_LIMIT_FAILURES", 5) or 5)
    lockout_seconds = int(getattr(settings, "LOGIN_RATE_LIMIT_LOCKOUT_SECONDS", 900) or 900)

    user_failures = _increment_counter(_cache_key("login_fail_user", normalized_username), window)
    ip_failures = _increment_counter(_cache_key("login_fail_ip", client_ip), window)
    create_log(
        log_type="USER",
        severity="WARNING",
        message="Failed login attempt",
        metadata={
            "username": normalized_username,
            "client_ip": client_ip,
            "user_failures": user_failures,
            "ip_failures": ip_failures,
        },
    )

    if user_failures < max_attempts and ip_failures < max_attempts:
        return None

    blocked_until = time.time() + lockout_seconds
    cache.set(_cache_key("login_block_user", normalized_username), blocked_until, lockout_seconds)
    cache.set(_cache_key("login_block_ip", client_ip), blocked_until, lockout_seconds)
    create_log(
        log_type="SYSTEM",
        severity="WARNING",
        message="Login rate limit triggered",
        metadata={
            "username": normalized_username,
            "client_ip": client_ip,
            "retry_after_seconds": lockout_seconds,
        },
    )
    return _build_lockout_state(normalized_username, client_ip)


def clear_login_failures(request, username):
    normalized_username = (username or "").strip().lower()
    client_ip = get_client_ip(request)
    for prefix in (
        "login_fail_user",
        "login_fail_ip",
        "login_block_user",
        "login_block_ip",
    ):
        cache.delete(_cache_key(prefix, normalized_username if "user" in prefix else client_ip))


def get_public_base_url(request):
    configured_base_url = (getattr(settings, "PUBLIC_BASE_URL", "") or "").strip()
    if configured_base_url:
        return configured_base_url.rstrip("/")
    return request.build_absolute_uri("/").rstrip("/")


def get_default_post_login_redirect(user):
    if getattr(user, "user_type", "") == "CLIENTE":
        return reverse("customer_portal:dashboard")
    return reverse("dashboard")


def get_safe_referer_redirect(request, fallback_url):
    referer = (request.META.get("HTTP_REFERER") or "").strip()
    if not referer:
        return fallback_url

    allowed_hosts = {request.get_host()}
    allowed_hosts.update(host for host in getattr(settings, "ALLOWED_HOSTS", []) if host and host != "*")
    is_secure = request.is_secure() or urlparse(fallback_url).scheme == "https"
    if url_has_allowed_host_and_scheme(referer, allowed_hosts=allowed_hosts, require_https=is_secure):
        return referer

    create_log(
        log_type="SYSTEM",
        severity="WARNING",
        user=request.user if request.user.is_authenticated else None,
        message="Unsafe redirect target rejected",
        metadata={"referer": referer, "path": request.path},
    )
    return fallback_url
