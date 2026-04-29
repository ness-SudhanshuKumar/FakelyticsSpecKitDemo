"""Authentication and rate-limiting dependencies for API routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Tuple
import hmac

from fastapi import Header, HTTPException, Response, status

from src.core.config.settings import settings


@dataclass(frozen=True)
class AuthContext:
    """Resolved identity and quota metadata for the current request."""

    api_key: str
    tier: str
    daily_limit: int


class InMemoryRateLimiter:
    """Simple per-key, per-endpoint daily quota tracker."""

    def __init__(self) -> None:
        self._usage: Dict[Tuple[str, str, str], int] = {}
        self._reset_at: Dict[Tuple[str, str], datetime] = {}
        self._lock = Lock()

    @staticmethod
    def _window_key() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    def check_and_increment(
        self,
        api_key: str,
        endpoint: str,
        limit: int,
    ) -> tuple[int, int, int]:
        """
        Reserve one request in the current daily window.

        Returns:
            tuple: (remaining, limit, retry_after_seconds)
        """
        now = datetime.utcnow()
        day = self._window_key()
        endpoint_key = (api_key, endpoint)
        usage_key = (api_key, endpoint, day)

        with self._lock:
            reset_at = self._reset_at.get(endpoint_key)
            if reset_at is None or now >= reset_at:
                tomorrow = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                self._reset_at[endpoint_key] = tomorrow
                # Drop stale entries for this endpoint key.
                for key in [k for k in self._usage if k[0] == api_key and k[1] == endpoint and k[2] != day]:
                    self._usage.pop(key, None)

            current = self._usage.get(usage_key, 0)
            if current >= limit:
                retry_after = int((self._reset_at[endpoint_key] - now).total_seconds())
                return 0, limit, max(retry_after, 1)

            current += 1
            self._usage[usage_key] = current
            remaining = max(0, limit - current)
            retry_after = int((self._reset_at[endpoint_key] - now).total_seconds())
            return remaining, limit, max(retry_after, 1)


rate_limiter = InMemoryRateLimiter()


def _resolve_tier(api_key: str) -> tuple[str, int]:
    """Map API key patterns to configured quotas."""
    lowered = api_key.lower()
    if lowered.startswith("pro_"):
        return "pro", settings.RATE_LIMIT_PRO_TIER
    if lowered.startswith("ent_") or lowered.startswith("enterprise_"):
        return "enterprise", settings.RATE_LIMIT_ENTERPRISE_TIER
    return "free", settings.RATE_LIMIT_FREE_TIER


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    """Validate API key and return request auth context."""
    candidate = (x_api_key or "").strip()
    valid_keys = settings.API_KEYS or [settings.API_KEY]
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Missing API key"},
        )

    key_is_valid = any(hmac.compare_digest(candidate, valid_key) for valid_key in valid_keys)
    if not key_is_valid and not hmac.compare_digest(candidate, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Invalid API key"},
        )

    tier, daily_limit = _resolve_tier(candidate)
    return AuthContext(api_key=candidate, tier=tier, daily_limit=daily_limit)


def enforce_rate_limit(
    response: Response,
    auth: AuthContext,
    endpoint: str,
) -> None:
    """Apply per-endpoint quota and set rate-limit headers."""
    remaining, limit, retry_after = rate_limiter.check_and_increment(
        api_key=auth.api_key,
        endpoint=endpoint,
        limit=auth.daily_limit,
    )

    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(retry_after)
    response.headers["X-RateLimit-Tier"] = auth.tier

    if remaining <= 0:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Rate limit exceeded for this API key",
                "details": {"tier": auth.tier, "retry_after": retry_after},
            },
        )

