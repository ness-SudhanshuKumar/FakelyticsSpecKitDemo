"""Webhook delivery service with retry/backoff."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from typing import Optional
from uuid import UUID

import httpx

from src.api.models.schemas import CredibilityReport, WebhookPayload
from src.core.config.settings import settings

logger = logging.getLogger(__name__)


def _build_headers(payload_json: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    secret = settings.WEBHOOK_SIGNING_SECRET
    if secret:
        signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=payload_json.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers["X-Fakelytics-Signature"] = f"sha256={signature}"
    return headers


async def post_webhook_result(
    webhook_url: str,
    request_id: UUID,
    status: str,
    report: Optional[CredibilityReport] = None,
    error_message: Optional[str] = None,
) -> bool:
    """POST webhook payload with retries and exponential backoff."""
    payload = WebhookPayload(
        request_id=request_id,
        status=status,
        report=report,
        error_message=error_message,
    )
    payload_json = json.dumps(payload.model_dump(mode="json"))
    headers = _build_headers(payload_json)

    timeout = httpx.Timeout(settings.WEBHOOK_TIMEOUT)
    retries = max(1, settings.WEBHOOK_RETRIES)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(retries):
            try:
                response = await client.post(webhook_url, content=payload_json, headers=headers)
                if 200 <= response.status_code < 300:
                    logger.info("Webhook delivered", extra={"request_id": str(request_id), "webhook_url": webhook_url})
                    return True
                logger.warning(
                    "Webhook non-2xx response",
                    extra={
                        "request_id": str(request_id),
                        "webhook_url": webhook_url,
                        "status_code": response.status_code,
                        "attempt": attempt + 1,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "Webhook delivery error",
                    extra={
                        "request_id": str(request_id),
                        "webhook_url": webhook_url,
                        "attempt": attempt + 1,
                        "error": str(exc),
                    },
                )

            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)

    logger.error("Webhook delivery failed after retries", extra={"request_id": str(request_id), "webhook_url": webhook_url})
    return False

