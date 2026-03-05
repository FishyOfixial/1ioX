from importlib import import_module
from typing import Any


def _load_local_overrides():
    try:
        return import_module("services.external_api_local")
    except ModuleNotFoundError:
        return None


def _call_local(function_name: str, payload: dict[str, Any]):
    module = _load_local_overrides()
    if module is None:
        return None

    fn = getattr(module, function_name, None)
    if not callable(fn):
        return None
    return fn(payload)


def call_1nce_api(payload: dict[str, Any]):
    return _call_local("call_1nce_api", payload)


def call_mercadopago_api(payload: dict[str, Any]):
    return _call_local("call_mercadopago_api", payload)


def get_cron_override(payload: dict[str, Any]):
    return _call_local("get_cron_override", payload)
