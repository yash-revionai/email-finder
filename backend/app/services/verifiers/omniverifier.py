from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.services.verifiers.base import BaseVerifier, VerifierResult

STATUS_MAP = {
    "valid": "valid",
    "invalid": "invalid",
    "accept_all": "catch_all",
    "accept-all": "catch_all",
    "accept all": "catch_all",
    "catch_all": "catch_all",
    "catch-all": "catch_all",
    "catch all": "catch_all",
    "unknown": "unknown",
}


class OmniVerifier(BaseVerifier):
    name = "omniverifier"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or settings.omniverifier_api_key
        self._http_client = http_client

    async def verify(self, email: str) -> VerifierResult:
        if not self.api_key:
            raise ValueError("OMNIVERIFIER_API_KEY is not configured")

        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(
            base_url=settings.omniverifier_base_url,
            timeout=settings.omniverifier_timeout_seconds,
        )
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        try:
            response = await client.post(
                settings.omniverifier_validate_path,
                json={"email": email},
                headers=headers,
            )
            return self._parse_response(response)
        finally:
            if owns_client:
                await client.aclose()

    def _parse_response(self, response: httpx.Response) -> VerifierResult:
        payload = _safe_json(response)

        if response.status_code >= 400:
            error = str(payload.get("error") or response.text or "OmniVerifier request failed").strip()
            code = str(payload.get("code") or "OMNIVERIFIER_ERROR").strip()
            raise RuntimeError(f"OmniVerifier error ({code}): {error}")

        raw_status = str(payload.get("status", "")).strip().lower()
        if not raw_status:
            raise RuntimeError(f"OmniVerifier response did not include a status: {payload}")

        normalized_status = STATUS_MAP.get(raw_status, "unknown")
        return VerifierResult(
            result=normalized_status,
            reason=raw_status,
            credits_used=1,
        )


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}

    if isinstance(payload, dict):
        return payload

    return {}
