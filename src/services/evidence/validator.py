"""Evidence validation utilities."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

import httpx

from src.api.models.schemas import Evidence
from src.core.config.settings import settings


async def validate_evidence_sources(evidence_items: Iterable[Evidence]) -> List[Evidence]:
    """Validate accessibility of evidence URLs and annotate records."""
    validated: List[Evidence] = []
    timeout = httpx.Timeout(settings.WEBHOOK_TIMEOUT)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for item in evidence_items:
            is_valid = False
            try:
                response = await client.head(item.url)
                is_valid = response.status_code < 400
            except Exception:
                is_valid = False

            item.validated = is_valid
            item.validated_at = datetime.utcnow()
            validated.append(item)

    return validated

