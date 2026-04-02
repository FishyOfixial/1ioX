import logging
import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from django.conf import settings
from auditlogs.utils import create_log
from services.external_api import call_1nce_api

logger = logging.getLogger("billing.1nce")


class OneNCEClient:
    def __init__(self) -> None:
        base_url = getattr(settings, "ONE_NCE_BASE_URL", "") or ""
        self.base_url = base_url.rstrip("/") + "/" if base_url else ""
        self.auth_url = (getattr(settings, "ONE_NCE_AUTH_URL", "") or "").strip()
        self.auth_header = (getattr(settings, "ONE_NCE_AUTH_HEADER", "") or "").strip()
        self.timeout = int(getattr(settings, "ONE_NCE_TIMEOUT", 30) or 30)
        self.pool_connections = int(getattr(settings, "ONE_NCE_POOL_CONNECTIONS", 10) or 10)
        self.pool_maxsize = int(getattr(settings, "ONE_NCE_POOL_MAXSIZE", 10) or 10)
        self.pool_block = getattr(settings, "ONE_NCE_POOL_BLOCK", True)

        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            pool_block=self.pool_block,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _token_is_valid(self) -> bool:
        return bool(self._access_token and time.time() < self._token_expires_at)

    def _resolve_auth_url(self) -> str:
        if self.auth_url:
            return self.auth_url
        if self.base_url:
            return f"{self.base_url}oauth/token"
        return ""

    def _build_credential_auth_header(self) -> str:
        if self.auth_header:
            return self.auth_header
        return ""

    def _refresh_token(self) -> bool:
        simulated = call_1nce_api({"method": "POST", "endpoint": "oauth/token", "payload": {"grant_type": "client_credentials"}})
        if simulated is not None:
            self._access_token = "simulated_token"
            self._token_expires_at = time.time() + 3600
            return True

        auth_url = self._resolve_auth_url()
        auth_header = self._build_credential_auth_header()

        if not auth_url:
            logger.error("1NCE auth not configured. Missing ONE_NCE_BASE_URL or ONE_NCE_AUTH_URL")
            return False
        if not auth_header:
            logger.error("1NCE auth not configured. Missing ONE_NCE_AUTH_HEADER/API_AUTH_HEADER")
            return False

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": auth_header,
        }
        payload = {"grant_type": "client_credentials"}

        try:
            response = self.session.post(auth_url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            body = response.json()

            token = body.get("access_token")
            expires_in = int(body.get("expires_in", 3600))
            if not token:
                logger.error("1NCE auth response without access_token")
                return False

            self._access_token = token
            self._token_expires_at = time.time() + max(expires_in - 60, 1)
            return True
        except requests.RequestException as exc:
            logger.error("1NCE auth failed: %s", exc, exc_info=True)
            create_log(
                log_type="SYSTEM",
                severity="ERROR",
                message="1NCE auth failed",
                metadata={"error": str(exc)},
            )
            return False
        except (TypeError, ValueError) as exc:
            logger.error("1NCE auth parse failed: %s", exc, exc_info=True)
            create_log(
                log_type="SYSTEM",
                severity="ERROR",
                message="1NCE auth parse failed",
                metadata={"error": str(exc)},
            )
            return False

    def _ensure_token(self) -> bool:
        if self._token_is_valid():
            return True
        return self._refresh_token()

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_payload: Optional[dict[str, Any] | list[dict[str, Any]]] = None,
        allow_retry_401: bool = True,
    ) -> Optional[requests.Response]:
        simulated = call_1nce_api({"method": method, "endpoint": endpoint, "payload": json_payload})
        if simulated is not None:
            return simulated

        if not self._ensure_token():
            return None

        if not self.base_url:
            logger.error("1NCE base url missing. ONE_NCE_BASE_URL/API_URL not configured")
            return None

        url = f"{self.base_url}{endpoint.lstrip('/')}"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._access_token}",
        }
        if json_payload is not None:
            headers["content-type"] = "application/json"

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                json=json_payload,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code == 401 and allow_retry_401:
                logger.warning("1NCE returned 401, refreshing token and retrying once")
                self._access_token = None
                self._token_expires_at = 0.0
                if not self._ensure_token():
                    return None
                return self._request(
                    method,
                    endpoint,
                    json_payload=json_payload,
                    allow_retry_401=False,
                )

            return response
        except requests.Timeout as exc:
            logger.error("1NCE timeout calling %s %s: %s", method.upper(), url, exc, exc_info=True)
            create_log(
                log_type="SYSTEM",
                severity="ERROR",
                message="1NCE timeout",
                metadata={"method": method.upper(), "url": url, "error": str(exc)},
            )
            return None
        except requests.RequestException as exc:
            logger.error("1NCE request error calling %s %s: %s", method.upper(), url, exc, exc_info=True)
            create_log(
                log_type="SYSTEM",
                severity="ERROR",
                message="1NCE request error",
                metadata={"method": method.upper(), "url": url, "error": str(exc)},
            )
            return None

    def _change_sim_status(self, iccid: str, status: str) -> bool:
        response = self._request(
            "put",
            f"sims/{iccid}",
            json_payload={"iccid": iccid, "status": status},
        )
        if response is None:
            return False
        if 200 <= response.status_code < 300:
            return True

        logger.error(
            "1NCE failed to update SIM status. iccid=%s status=%s http_status=%s",
            iccid,
            status,
            response.status_code,
        )
        return False

    def enable_sim(self, iccid: str) -> bool:
        return self._change_sim_status(iccid, "Enabled")

    def disable_sim(self, iccid: str) -> bool:
        return self._change_sim_status(iccid, "Disabled")

    def get_sim_status(self, iccid: str) -> str:
        response = self._request("get", f"sims/{iccid}/status")
        if response is None:
            return ""
        if not (200 <= response.status_code < 300):
            logger.error(
                "1NCE failed to fetch SIM status. iccid=%s http_status=%s",
                iccid,
                response.status_code,
            )
            return ""

        try:
            payload = response.json()
            return str(payload.get("status") or payload.get("simStatus") or "")
        except ValueError as exc:
            logger.error("1NCE invalid JSON in SIM status response. iccid=%s err=%s", iccid, exc, exc_info=True)
            return ""
