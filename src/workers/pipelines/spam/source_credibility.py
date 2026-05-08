"""Source credibility scoring for domain reputation analysis."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)


class SourceCredibility(str, Enum):
    """Source credibility levels."""
    HIGHLY_CREDIBLE = "highly_credible"
    CREDIBLE = "credible"
    NEUTRAL = "neutral"
    LOW_CREDIBILITY = "low_credibility"
    SUSPICIOUS = "suspicious"


@dataclass
class SSLInfo:
    """SSL/TLS certificate information."""
    has_ssl: bool
    is_valid: bool
    certificate_issued_date: Optional[str] = None
    certificate_expiry_date: Optional[str] = None
    certificate_issuer: Optional[str] = None
    protocol_version: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DomainInfo:
    """Domain registration and age information."""
    domain: str
    is_registered: bool
    age_years: Optional[float] = None
    registration_date: Optional[str] = None
    last_updated_date: Optional[str] = None
    registrar: Optional[str] = None
    is_typosquat: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SourceCredibilityScore:
    """Overall source credibility assessment."""
    domain: str
    credibility_level: SourceCredibility
    credibility_score: int  # 0-100
    ssl_info: SSLInfo
    domain_info: DomainInfo
    reputation_score: int  # 0-100
    trust_indicators: list[str]
    risk_indicators: list[str]
    summary: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "credibility_level": self.credibility_level.value,
            "credibility_score": self.credibility_score,
            "ssl_info": self.ssl_info.to_dict(),
            "domain_info": self.domain_info.to_dict(),
            "reputation_score": self.reputation_score,
            "trust_indicators": self.trust_indicators,
            "risk_indicators": self.risk_indicators,
            "summary": self.summary,
        }


class DomainReputation:
    """Reputation blocklist checking."""

    # Known trustworthy domains (simplified for demo)
    TRUSTED_DOMAINS = {
        "wikipedia.org": 95,
        "bbc.com": 90,
        "reuters.com": 90,
        "apnews.com": 85,
        "nytimes.com": 85,
        "theguardian.com": 85,
        "bbc.co.uk": 90,
        "gov.uk": 95,
        "edu": 80,
        "org": 70,
    }

    # Suspicious patterns
    SUSPICIOUS_PATTERNS = {
        r"^admin-": "Administrative domain",
        r"-confirm-": "Phishing indicator",
        r"verify-": "Verification phishing",
        r"update-": "Update phishing",
        r"secure-login": "Fake secure login",
    }

    @staticmethod
    def check_trusted_domain(domain: str) -> Optional[int]:
        """Check if domain is in trusted list."""
        domain_lower = domain.lower()

        # Exact matches
        if domain_lower in DomainReputation.TRUSTED_DOMAINS:
            return DomainReputation.TRUSTED_DOMAINS[domain_lower]

        # TLD matches
        parts = domain_lower.split(".")
        if len(parts) > 1:
            tld = parts[-1]
            if tld in DomainReputation.TRUSTED_DOMAINS:
                return DomainReputation.TRUSTED_DOMAINS[tld]

            # Subdomain of trusted domain
            for trusted, score in DomainReputation.TRUSTED_DOMAINS.items():
                if domain_lower.endswith("." + trusted):
                    return score - 5  # Slightly lower for subdomains

        return None

    @staticmethod
    def detect_typosquatting(domain: str) -> bool:
        """Detect typosquatting patterns."""
        domain_lower = domain.lower()

        # Check for suspicious patterns
        for pattern in DomainReputation.SUSPICIOUS_PATTERNS:
            if re.search(pattern, domain_lower):
                return True

        # Check for common misspellings of popular domains
        common_typos = {
            "goggle.com": "google.com",
            "faecbook.com": "facebook.com",
            "twiter.com": "twitter.com",
            "redddit.com": "reddit.com",
            "amzon.com": "amazon.com",
        }

        if domain_lower in common_typos:
            return True

        return False


class SourceCredibilityAnalyzer:
    """Analyzes source credibility based on domain reputation and SSL."""

    def __init__(self):
        """Initialize the analyzer."""
        self.reputation = DomainReputation()

    async def analyze_url(self, url: str, timeout: int = 10) -> SourceCredibilityScore:
        """
        Analyze URL source credibility.

        Args:
            url: URL to analyze
            timeout: Analysis timeout in seconds

        Returns:
            SourceCredibilityScore with credibility assessment

        Raises:
            ValueError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL: must be non-empty string")

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if not domain:
                raise ValueError("Invalid URL: no domain found")

        except Exception as e:
            logger.error(f"URL parsing error for {url}: {e}")
            raise ValueError(f"Invalid URL format: {str(e)}")

        try:
            result = await asyncio.wait_for(
                self._perform_analysis(url, domain),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Source credibility analysis timed out after {timeout}s")
            raise

    async def _perform_analysis(self, url: str, domain: str) -> SourceCredibilityScore:
        """Perform the actual analysis."""
        # Check SSL
        ssl_info = await self._check_ssl(url)

        # Get domain info
        domain_info = await self._get_domain_info(domain)

        # Check reputation
        trusted_score = self.reputation.check_trusted_domain(domain)
        is_typosquat = self.reputation.detect_typosquatting(domain)

        # Calculate reputation score
        reputation_score = trusted_score if trusted_score else 50

        # Determine trust and risk indicators
        trust_indicators = []
        risk_indicators = []

        # SSL indicators
        if ssl_info.has_ssl:
            trust_indicators.append("HTTPS/SSL enabled")
        else:
            risk_indicators.append("No HTTPS encryption")

        # Domain age indicators
        if domain_info.age_years is not None:
            if domain_info.age_years > 5:
                trust_indicators.append(f"Domain established {int(domain_info.age_years)}+ years ago")
            elif domain_info.age_years < 1:
                risk_indicators.append("Recently registered domain")

        # Typosquatting indicator
        if is_typosquat:
            risk_indicators.append("Potential typosquatting detected")

        # Reputation indicators
        if trusted_score and trusted_score > 80:
            trust_indicators.append("Domain on trusted list")
        elif reputation_score < 40:
            risk_indicators.append("Low domain reputation")

        # Calculate final credibility score
        credibility_score = self._calculate_credibility_score(
            ssl_info, domain_info, reputation_score, is_typosquat
        )

        # Determine credibility level
        credibility_level = self._determine_credibility_level(credibility_score)

        # Generate summary
        summary = self._generate_summary(
            domain, credibility_level, trust_indicators, risk_indicators
        )

        return SourceCredibilityScore(
            domain=domain,
            credibility_level=credibility_level,
            credibility_score=credibility_score,
            ssl_info=ssl_info,
            domain_info=domain_info,
            reputation_score=reputation_score,
            trust_indicators=trust_indicators,
            risk_indicators=risk_indicators,
            summary=summary,
        )

    async def _check_ssl(self, url: str) -> SSLInfo:
        """Check SSL/TLS configuration."""
        try:
            parsed = urlparse(url)
            has_ssl = parsed.scheme == "https"

            # For demo, we assume HTTPS is valid if present
            return SSLInfo(
                has_ssl=has_ssl,
                is_valid=has_ssl,
                protocol_version="TLS 1.2+" if has_ssl else None,
            )
        except Exception as e:
            logger.debug(f"Error checking SSL: {e}")
            return SSLInfo(has_ssl=False, is_valid=False)

    async def _get_domain_info(self, domain: str) -> DomainInfo:
        """Get domain registration information."""
        # For demo, estimate domain age based on patterns
        # In production, would use WHOIS API
        age_years = None

        # Simulate domain age estimation
        domain_lower = domain.lower()
        if domain_lower.endswith(".gov") or domain_lower.endswith(".gov.uk") or domain_lower.endswith(".edu"):
            age_years = 10.0  # Assume old
        elif domain_lower.endswith(".org"):
            age_years = 8.0
        elif domain_lower.endswith(".com"):
            age_years = 5.0
        else:
            age_years = 2.0

        return DomainInfo(
            domain=domain,
            is_registered=True,
            age_years=age_years,
            registrar="ICANN Registrar",
            is_typosquat=self.reputation.detect_typosquatting(domain),
        )

    @staticmethod
    def _calculate_credibility_score(
        ssl_info: SSLInfo,
        domain_info: DomainInfo,
        reputation_score: int,
        is_typosquat: bool,
    ) -> int:
        """Calculate overall credibility score."""
        score = reputation_score

        # SSL boost
        if ssl_info.has_ssl and ssl_info.is_valid:
            score = min(100, score + 10)
        else:
            score = max(0, score - 10)

        # Domain age boost
        if domain_info.age_years and domain_info.age_years > 5:
            score = min(100, score + 5)
        elif domain_info.age_years and domain_info.age_years < 1:
            score = max(0, score - 20)

        # Typosquatting penalty
        if is_typosquat:
            score = max(0, score - 30)

        return max(0, min(100, score))

    @staticmethod
    def _determine_credibility_level(score: int) -> SourceCredibility:
        """Determine credibility level from score."""
        if score >= 85:
            return SourceCredibility.HIGHLY_CREDIBLE
        elif score >= 70:
            return SourceCredibility.CREDIBLE
        elif score >= 50:
            return SourceCredibility.NEUTRAL
        elif score >= 30:
            return SourceCredibility.LOW_CREDIBILITY
        else:
            return SourceCredibility.SUSPICIOUS

    @staticmethod
    def _generate_summary(
        domain: str,
        level: SourceCredibility,
        trust_indicators: list[str],
        risk_indicators: list[str],
    ) -> str:
        """Generate human-readable summary."""
        level_text = {
            SourceCredibility.HIGHLY_CREDIBLE: "highly credible",
            SourceCredibility.CREDIBLE: "credible",
            SourceCredibility.NEUTRAL: "neutral credibility",
            SourceCredibility.LOW_CREDIBILITY: "low credibility",
            SourceCredibility.SUSPICIOUS: "suspicious",
        }

        text = f"Domain '{domain}' has {level_text[level]}."

        if risk_indicators:
            text += f" Risk factors: {'; '.join(risk_indicators)}."

        if trust_indicators:
            text += f" Trust indicators: {'; '.join(trust_indicators)}."

        return text


# Global singleton instance
_source_analyzer: Optional[SourceCredibilityAnalyzer] = None


def get_source_analyzer() -> SourceCredibilityAnalyzer:
    """Get or create the global source analyzer instance."""
    global _source_analyzer
    if _source_analyzer is None:
        _source_analyzer = SourceCredibilityAnalyzer()
    return _source_analyzer


async def analyze_source_credibility(url: str, timeout: int = 10) -> dict:
    """
    Async task wrapper for source credibility analysis.

    Args:
        url: URL to analyze
        timeout: Analysis timeout in seconds

    Returns:
        Dictionary representation of SourceCredibilityScore
    """
    analyzer = get_source_analyzer()
    score = await analyzer.analyze_url(url, timeout=timeout)
    return score.to_dict()
