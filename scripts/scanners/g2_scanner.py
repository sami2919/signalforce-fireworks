"""G2 Review Signal Scanner.

Detects companies publicly expressing frustration with Marketo or HubSpot
via G2 reviews indexed by search engines. A VP Marketing leaving a negative
G2 review is a high-intent migration signal.

Signal type: "g2_review_frustration"
Strength:
  - Contains "migration", "replacing", "alternative", "evaluating" → STRONG
  - Contains "complex", "expensive", "slow", "frustrating"        → MODERATE
  - Any other frustration language                                 → WEAK
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from scripts.scanners.base import ScannerConfig, ScanResult, Signal, SignalStrength

logger = logging.getLogger(__name__)

_STRONG_KEYWORDS = {"migration", "replacing", "alternative", "evaluating", "switching", "replacement"}
_MODERATE_KEYWORDS = {"complex", "expensive", "slow", "frustrating", "difficult", "overhead", "bloated"}

_G2_QUERIES: list[str] = [
    # Target individual review pages (URL path contains /reviews/), not competitor/alternatives pages
    'site:g2.com/products/adobe-marketo-engage/reviews "complex" OR "migration" OR "alternative"',
    'site:g2.com/products/adobe-marketo-engage/reviews "expensive" OR "pricing" OR "adobe"',
    'site:g2.com/products/hubspot-marketing-hub/reviews "snowflake" OR "warehouse" OR "data team"',
    'site:g2.com/products/hubspot-marketing-hub/reviews "expensive" OR "enterprise" OR "ceiling"',
]


class G2ReviewScanner:
    """Scans for frustrated MAP (Marketo/HubSpot) reviews on G2 via SerpAPI."""

    def __init__(self, api_key: str | None = None) -> None:
        from scripts.scanners.job_scanner import JobPostingClient
        from scripts.config import get_config

        resolved_key = api_key if api_key is not None else get_config().serpapi_key
        self._client = JobPostingClient(api_key=resolved_key)

    def scan(self, lookback_days: int = 7) -> ScanResult:
        """Run G2 frustration scan across configured queries."""
        started_at = datetime.now(timezone.utc)
        signals: list[Signal] = []
        total_raw = 0
        errors: list[str] = []
        seen_urls: set[str] = set()

        for query in _G2_QUERIES:
            try:
                results = self._client.search_jobs(query, num_results=10)
            except Exception as exc:
                msg = f"G2 search failed for query '{query}': {exc}"
                logger.warning(msg)
                errors.append(msg)
                continue

            total_raw += len(results)
            for result in results:
                url = result.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                signal = self._result_to_signal(result)
                if signal is not None:
                    signals.append(signal)

        return ScanResult(
            scan_type="g2_review_frustration",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            signals_found=signals,
            total_raw_results=total_raw,
            total_after_dedup=len(signals),
            errors=errors,
        )

    def _result_to_signal(self, result: dict) -> Signal | None:
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        url = result.get("url", "")
        combined = (title + " " + snippet).lower()

        if "g2.com" not in url:
            return None

        company = self._extract_company(title, snippet)
        if not company:
            return None

        strength = self._score_frustration(combined)

        return Signal(
            signal_type="g2_review_frustration",
            company_name=company,
            signal_strength=strength,
            source_url=url,
            raw_data={"title": title, "snippet": snippet, "url": url},
            metadata={
                "review_platform": "G2",
                "product_reviewed": self._extract_product(combined),
                "frustration_keywords": self._found_keywords(combined),
            },
        )

    def _extract_company(self, title: str, snippet: str) -> str | None:
        patterns = [
            r"at\s+([A-Z][A-Za-z0-9][A-Za-z0-9\s&,\.]{1,35})(?:\s*[-–|]|$)",
            r"from\s+([A-Z][A-Za-z0-9][A-Za-z0-9\s&,\.]{1,35})(?:\s*[-–|]|$)",
            r"—\s+([A-Z][A-Za-z0-9][A-Za-z0-9\s&,\.]{1,35})$",
        ]
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                name = match.group(1).strip()
                if len(name) >= 2:
                    return name
        match = re.search(r"\bat\s+([A-Z][A-Za-z0-9]{2,})", snippet)
        if match:
            return match.group(1).strip()
        return None

    def _extract_product(self, text: str) -> str:
        if "marketo" in text:
            return "Marketo"
        if "hubspot" in text:
            return "HubSpot"
        if "pardot" in text:
            return "Pardot"
        return "Unknown MAP"

    def _score_frustration(self, text: str) -> SignalStrength:
        for kw in _STRONG_KEYWORDS:
            if kw in text:
                return SignalStrength.STRONG
        for kw in _MODERATE_KEYWORDS:
            if kw in text:
                return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def _found_keywords(self, text: str) -> list[str]:
        return [kw for kw in (_STRONG_KEYWORDS | _MODERATE_KEYWORDS) if kw in text]


def scan(config: ScannerConfig) -> ScanResult:
    """Run a G2 frustration scan using ScannerConfig."""
    scanner = G2ReviewScanner()
    return scanner.scan(config.lookback_days)
