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
            logger.info("MercadoPago request: %s %s", method.upper(), url)
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                json=json_payload,
                timeout=self.timeout,
            )
            logger.info("MercadoPago response: %s %s -> %s", method.upper(), url, response.status_code)
            return response
        except requests.Timeout as exc:
            logger.error("MercadoPago timeout: %s", exc, exc_info=True)
            return None
        except requests.RequestException as exc:
            logger.error("MercadoPago request error: %s", exc, exc_info=True)
            return None

    def create_preference(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        response = self._request("post", "/checkout/preferences", json_payload=payload)
        if response is None:
            return None
        if not (200 <= response.status_code < 300):
            logger.error("MercadoPago create preference failed: status=%s body=%s", response.status_code, response.text)
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
