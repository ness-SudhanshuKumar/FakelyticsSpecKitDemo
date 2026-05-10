"""Evidence validation for verification findings."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class EvidenceValidation:
    """Result of evidence URL validation."""
    url: str
    is_accessible: bool
    status_code: Optional[int] = None
    title: Optional[str] = None
    snippet_preview: Optional[str] = None
    validation_error: Optional[str] = None
    last_validated: Optional[str] = None
    response_time_ms: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class EvidenceValidator:
    """Validates evidence URLs and checks accessibility."""

    # Maximum time to wait for a response (seconds)
    DEFAULT_TIMEOUT = 10

    # Maximum content to read from response (bytes)
    MAX_CONTENT_SIZE = 100_000

    # Retry configuration
    MAX_RETRIES = 2
    RETRY_DELAY = 1  # seconds

    # User agent
    USER_AGENT = "Fakelytics/1.0 (Evidence Validation)"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """Initialize validator."""
        self.timeout = timeout

    async def validate_evidence_url(self, url: str) -> EvidenceValidation:
        """
        Validate an evidence URL by checking accessibility and extracting metadata.

        Args:
            url: URL to validate

        Returns:
            EvidenceValidation with accessibility status and metadata

        Raises:
            ValueError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL: must be non-empty string")

        # Validate URL format
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL format: {url}")
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Unsupported scheme: {parsed.scheme}")
        except Exception as e:
            logger.error(f"URL parsing error for {url}: {e}")
            return EvidenceValidation(
                url=url,
                is_accessible=False,
                validation_error=f"Invalid URL format: {str(e)}",
            )

        # Block private/local IPs
        if self._is_private_ip(parsed.netloc):
            return EvidenceValidation(
                url=url,
                is_accessible=False,
                validation_error="Access to private IP addresses is blocked",
            )

        # Try to fetch URL with retries
        return await self._fetch_and_validate(url)

    async def _fetch_and_validate(self, url: str) -> EvidenceValidation:
        """Fetch URL and extract metadata."""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    start_time = asyncio.get_event_loop().time()
                    async with session.get(
                        url,
                        headers={"User-Agent": self.USER_AGENT},
                        allow_redirects=True,
                        ssl=False,  # Note: in production, use proper SSL verification
                    ) as resp:
                        end_time = asyncio.get_event_loop().time()
                        response_time = (end_time - start_time) * 1000  # Convert to ms

                        if resp.status == 200:
                            # Successfully fetched - extract metadata
                            content = await resp.content.read(self.MAX_CONTENT_SIZE)
                            title, snippet = await self._extract_metadata(content)

                            return EvidenceValidation(
                                url=url,
                                is_accessible=True,
                                status_code=resp.status,
                                title=title,
                                snippet_preview=snippet,
                                response_time_ms=response_time,
                            )
                        else:
                            # Non-200 status
                            return EvidenceValidation(
                                url=url,
                                is_accessible=False,
                                status_code=resp.status,
                                validation_error=f"HTTP {resp.status}",
                                response_time_ms=response_time,
                            )

            except asyncio.TimeoutError:
                error_msg = f"Request timeout after {self.timeout}s"
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"Timeout for {url}, retrying... (attempt {attempt + 1})")
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                return EvidenceValidation(
                    url=url,
                    is_accessible=False,
                    validation_error=error_msg,
                )

            except aiohttp.ClientError as e:
                error_msg = str(e)
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"Client error for {url}, retrying... (attempt {attempt + 1})")
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                return EvidenceValidation(
                    url=url,
                    is_accessible=False,
                    validation_error=error_msg,
                )

            except Exception as e:
                logger.error(f"Unexpected error validating {url}: {e}")
                return EvidenceValidation(
                    url=url,
                    is_accessible=False,
                    validation_error=f"Unexpected error: {type(e).__name__}",
                )

        # Exhausted retries
        return EvidenceValidation(
            url=url,
            is_accessible=False,
            validation_error="Failed after maximum retries",
        )

    async def _extract_metadata(self, content: bytes) -> tuple[Optional[str], Optional[str]]:
        """Extract title and snippet from HTML content."""
        try:
            if not content:
                return None, None

            soup = BeautifulSoup(content, "html.parser")

            # Extract title
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else None

            # Extract snippet (first paragraph or meta description)
            snippet = None
            meta_desc = soup.find("meta", {"name": "description"})
            if meta_desc and meta_desc.get("content"):
                snippet = meta_desc["content"][:200]
            else:
                # Fall back to first paragraph
                p_tag = soup.find("p")
                if p_tag:
                    snippet = p_tag.get_text(strip=True)[:200]

            return title, snippet

        except Exception as e:
            logger.debug(f"Error extracting metadata: {e}")
            return None, None

    @staticmethod
    def _is_private_ip(hostname: str) -> bool:
        """Check if hostname is a private/local IP."""
        private_prefixes = (
            "127.", "192.168.", "10.", "172.",  # Standard private ranges
            "localhost", "0.0.0.0", "255.255.255.255",
        )
        return any(hostname.startswith(prefix) for prefix in private_prefixes)


class EvidenceProcessor:
    """Process and validate multiple evidence items."""

    def __init__(self, timeout: int = 10, max_concurrent: int = 5):
        """
        Initialize evidence processor.

        Args:
            timeout: Individual request timeout in seconds
            max_concurrent: Maximum concurrent validation tasks
        """
        self.validator = EvidenceValidator(timeout=timeout)
        self.max_concurrent = max_concurrent

    async def validate_batch(
        self,
        evidence_urls: list[str],
        timeout_total: int = 60,
    ) -> dict[str, EvidenceValidation]:
        """
        Validate multiple evidence URLs concurrently.

        Args:
            evidence_urls: List of URLs to validate
            timeout_total: Total timeout for batch operation

        Returns:
            Dictionary mapping URL to EvidenceValidation result
        """
        if not evidence_urls:
            return {}

        # Create tasks with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def validate_with_semaphore(url: str) -> tuple[str, EvidenceValidation]:
            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        self.validator.validate_evidence_url(url),
                        timeout=self.validator.timeout * 2,
                    )
                    return url, result
                except asyncio.TimeoutError:
                    return url, EvidenceValidation(
                        url=url,
                        is_accessible=False,
                        validation_error="Batch validation timeout",
                    )

        try:
            # Run all validations with total timeout
            tasks = [validate_with_semaphore(url) for url in evidence_urls]
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=timeout_total,
            )
            return dict(results)

        except asyncio.TimeoutError:
            logger.warning(f"Batch validation exceeded total timeout of {timeout_total}s")
            # Return partial results for any that completed
            return {}

    async def validate_and_enrich(
        self,
        finding_data: dict,
    ) -> dict:
        """
        Validate evidence URLs in a finding and enrich with metadata.

        Args:
            finding_data: Finding dict with 'evidence' list

        Returns:
            Enriched finding dict with validation results
        """
        if "evidence" not in finding_data or not finding_data["evidence"]:
            return finding_data

        evidence_list = finding_data["evidence"]
        if not isinstance(evidence_list, list):
            return finding_data

        # Extract URLs
        urls = [
            ev.get("url") if isinstance(ev, dict) else getattr(ev, "url", None)
            for ev in evidence_list
            if ev
        ]
        urls = [u for u in urls if u]

        if not urls:
            return finding_data

        # Validate batch
        validations = await self.validate_batch(urls)

        # Enrich evidence with validation results
        enriched_evidence = []
        for ev in evidence_list:
            if isinstance(ev, dict):
                url = ev.get("url")
                if url in validations:
                    ev["validation"] = validations[url].to_dict()
                enriched_evidence.append(ev)
            else:
                # Handle non-dict evidence objects
                enriched_evidence.append(ev)

        finding_data["evidence"] = enriched_evidence
        return finding_data


# Global singleton instance
_evidence_processor: Optional[EvidenceProcessor] = None


def get_evidence_processor(timeout: int = 10, max_concurrent: int = 5) -> EvidenceProcessor:
    """Get or create the global evidence processor instance."""
    global _evidence_processor
    if _evidence_processor is None:
        _evidence_processor = EvidenceProcessor(timeout=timeout, max_concurrent=max_concurrent)
    return _evidence_processor
