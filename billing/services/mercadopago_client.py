import logging
from typing import Any, Optional

import requests
from django.conf import settings

logger = logging.getLogger("billing.mercadopago")


class MercadoPagoClient:
    def __init__(self) -> None:
        self.base_url = (settings.MERCADOPAGO_BASE_URL or "https://api.mercadopago.com").rstrip("/")
        self.access_token = settings.MERCADOPAGO_ACCESS_TOKEN or ""
        self.timeout = settings.MERCADOPAGO_TIMEOUT
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_payload: Optional[dict[str, Any]] = None,
    ) -> Optional[requests.Response]:
        if not self.access_token:
            logger.error("Mercado Pago access token not configured")
            return None

        url = f"{self.base_url}{endpoint}"
        try:
            logger.debug("MercadoPago request: %s %s", method.upper(), url)
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                json=json_payload,
                timeout=self.timeout,
            )
            logger.debug("MercadoPago response: %s %s -> %s", method.upper(), url, response.status_code)
            return response
        except requests.Timeout as exc:
            logger.error("MercadoPago timeout: %s", exc, exc_info=True)
            return None
        except requests.RequestException as exc:
            logger.error("MercadoPago request error: %s", exc, exc_info=True)
            return None

    def create_preference(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        payload = dict(payload)
        payment_methods = payload.get("payment_methods")
        if not isinstance(payment_methods, dict):
            payment_methods = {}

        payment_methods["installments"] = 1
        payment_methods["default_installments"] = 1
        payload["payment_methods"] = payment_methods

        response = self._request("post", "/checkout/preferences", json_payload=payload)
        if response is None:
            return None
        if not (200 <= response.status_code < 300):
            should_retry_without_auto_return = False
            if response.status_code == 400:
                try:
                    body = response.json()
                    if body.get("error") == "invalid_auto_return":
                        should_retry_without_auto_return = True
                except ValueError:
                    should_retry_without_auto_return = False

            if should_retry_without_auto_return and payload.get("auto_return"):
                logger.warning(
                    "MercadoPago rejected auto_return. Retrying preference creation without auto_return."
                )
                fallback_payload = dict(payload)
                fallback_payload.pop("auto_return", None)
                retry_response = self._request("post", "/checkout/preferences", json_payload=fallback_payload)
                if retry_response is not None and (200 <= retry_response.status_code < 300):
                    try:
                        return retry_response.json()
                    except ValueError:
                        logger.error("MercadoPago preference retry returned invalid JSON")
                        return None

                logger.error(
                    "MercadoPago create preference retry failed: status=%s body=%s",
                    getattr(retry_response, "status_code", "n/a"),
                    getattr(retry_response, "text", "n/a"),
                )
                return None

            logger.error(
                "MercadoPago create preference failed: status=%s body=%s",
                response.status_code,
                response.text,
            )
            return None
        try:
            return response.json()
        except ValueError:
            logger.error("MercadoPago create preference invalid JSON response")
            return None

    def get_payment(self, payment_id: str) -> Optional[dict[str, Any]]:
        response = self._request("get", f"/v1/payments/{payment_id}")
        if response is None:
            return None
        if not (200 <= response.status_code < 300):
            logger.error("MercadoPago get payment failed: id=%s status=%s", payment_id, response.status_code)
            return None
        try:
            return response.json()
        except ValueError:
            logger.error("MercadoPago get payment invalid JSON response")
            return None

    def create_preapproval(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        response = self._request("post", "/preapproval", json_payload=payload)
        if response is None:
            return None
        if not (200 <= response.status_code < 300):
            logger.error(
                "MercadoPago create preapproval failed: status=%s body=%s",
                response.status_code,
                response.text,
            )
            return None
        try:
            return response.json()
        except ValueError:
            logger.error("MercadoPago create preapproval invalid JSON response")
            return None

    def get_preapproval(self, preapproval_id: str) -> Optional[dict[str, Any]]:
        response = self._request("get", f"/preapproval/{preapproval_id}")
        if response is None:
            return None
        if not (200 <= response.status_code < 300):
            logger.error(
                "MercadoPago get preapproval failed: id=%s status=%s",
                preapproval_id,
                response.status_code,
            )
            return None
        try:
            return response.json()
        except ValueError:
            logger.error("MercadoPago get preapproval invalid JSON response")
            return None

    def update_preapproval(self, preapproval_id: str, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        response = self._request("put", f"/preapproval/{preapproval_id}", json_payload=payload)
        if response is None:
            return None
        if not (200 <= response.status_code < 300):
            logger.error(
                "MercadoPago update preapproval failed: id=%s status=%s body=%s",
                preapproval_id,
                response.status_code,
                response.text,
            )
            return None
        try:
            return response.json()
        except ValueError:
            logger.error("MercadoPago update preapproval invalid JSON response")
            return None

    def cancel_preapproval(self, preapproval_id: str) -> bool:
        response = self.update_preapproval(preapproval_id, {"status": "cancelled"})
        return response is not None
