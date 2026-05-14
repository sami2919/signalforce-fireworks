"""G2 Authenticated Review Scanner.

Uses your G2 session cookie to fetch low-star reviews of MAP vendors
(Marketo, HubSpot Enterprise, Pardot) and extract company names.

Setup (one-time):
  1. Log into g2.com in your browser
  2. Open DevTools → Network → click any g2.com request → copy the Cookie header
  3. Add to .env:  G2_SESSION_COOKIE="<paste full cookie string>"

Usage:
  python -m scripts.scanners.g2_authenticated_scanner          # run scan
  python -m scripts.scanners.g2_authenticated_scanner --debug  # dump raw HTML for selector tuning
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Iterator

import requests
from bs4 import BeautifulSoup

from scripts.scanners.base import ScannerConfig, ScanResult, Signal, SignalStrength

logger = logging.getLogger(__name__)

_COOKIE_ENV_VAR = "G2_SESSION_COOKIE"

_MAP_VENDORS: list[dict] = [
    {"slug": "marketo", "display": "Marketo"},
    {"slug": "hubspot", "display": "HubSpot"},
    {"slug": "pardot", "display": "Pardot"},
]

# Star ratings to fetch — 1-3 are frustration signals
_STAR_RATINGS = [1, 2, 3]

_STRONG_KEYWORDS = {
    "migration", "replacing", "switching", "evaluating", "replacement",
    "alternative", "alternatives", "migrating", "moved off",
}
_MODERATE_KEYWORDS = {
    "expensive", "complex", "slow", "frustrating", "difficult",
    "overhead", "bloated", "ceiling", "too much", "painful", "clunky",
}

# G2 review page HTML selectors — tried in order, first match wins.
# G2 occasionally changes class names; multiple fallbacks keep it working.
_REVIEW_CARD_SELECTORS = [
    "[itemprop='review']",
    ".paper.p-lg-4",
    "[data-testid='review-card']",
    ".review-card",
    ".review-survey__answer",
]

_REVIEWER_TITLE_SELECTORS = [
    ".reviewer-info__title",
    "[itemprop='author'] + *",
    ".mt-4.review-author",
    ".reviewer-title",
    "[class*='reviewer']",
    "[class*='author-title']",
]

_REVIEW_BODY_SELECTORS = [
    "[itemprop='reviewBody']",
    ".formatted-text",
    "[data-testid='review-body']",
    ".review-body",
    "[class*='review-body']",
]

_STAR_SELECTORS = [
    "[itemprop='ratingValue']",
    "[class*='stars_v2']",
    "[aria-label*='star']",
    "[class*='star-rating']",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.g2.com/",
}

# Regex: "at CompanyName" from reviewer title text
_AT_COMPANY_RE = re.compile(
    r"\bat\s+([A-Z][A-Za-z0-9][A-Za-z0-9&.,\- ]{0,50}?)(?:\s*[|,·•\n]|$)"
)

_NON_COMPANIES = {
    "g2", "g2.com", "the time", "the company", "a startup", "my company",
    "a team", "our team", "a large", "a small", "work",
}


class G2AuthenticatedScanner:
    """Fetches G2 reviews using the user's own session cookie."""

    def __init__(self, cookie: str | None = None, debug: bool = False) -> None:
        resolved = cookie or os.environ.get(_COOKIE_ENV_VAR, "")
        if not resolved:
            logger.warning(
                "G2_SESSION_COOKIE not set. Add your G2 session cookie to .env. "
                "Instructions: log into g2.com → DevTools → Network → copy Cookie header."
            )
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        if resolved:
            self._session.headers["Cookie"] = resolved
        self._debug = debug

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def scan(self, lookback_days: int = 30) -> ScanResult:
        started_at = datetime.now(timezone.utc)

        if not self._session.headers.get("Cookie"):
            return ScanResult(
                scan_type="g2_review",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                signals_found=[],
                total_raw_results=0,
                total_after_dedup=0,
                errors=["G2_SESSION_COOKIE not configured — see .env.example"],
            )

        signals: list[Signal] = []
        seen: set[str] = set()
        total_raw = 0
        errors: list[str] = []

        for vendor in _MAP_VENDORS:
            for stars in _STAR_RATINGS:
                try:
                    reviews = list(self._fetch_reviews(vendor, stars))
                    total_raw += len(reviews)
                    for review in reviews:
                        company = review.get("company", "")
                        key = company.lower()
                        if not company or key in seen or key in _NON_COMPANIES:
                            continue
                        seen.add(key)
                        signals.append(self._to_signal(review, vendor["display"]))
                    # Be polite — G2 rate-limits aggressive requests
                    time.sleep(1.5)
                except Exception as exc:
                    msg = f"G2 fetch failed ({vendor['display']} ★{stars}): {exc}"
                    logger.warning(msg)
                    errors.append(msg)

        return ScanResult(
            scan_type="g2_review",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            signals_found=signals,
            total_raw_results=total_raw,
            total_after_dedup=len(signals),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _fetch_reviews(self, vendor: dict, stars: int) -> Iterator[dict]:
        url = (
            f"https://www.g2.com/products/{vendor['slug']}/reviews"
            f"?filters%5Bstar_rating%5D={stars}&filters%5Bsort%5D=recent"
        )
        resp = self._session.get(url, timeout=15)

        if self._debug:
            path = f"/tmp/g2_debug_{vendor['slug']}_{stars}star.html"
            with open(path, "w") as f:
                f.write(resp.text)
            logger.info("Debug HTML saved to %s (status %d)", path, resp.status_code)

        if resp.status_code == 403:
            raise RuntimeError(
                f"403 Forbidden — cookie may be expired. "
                f"Re-copy from DevTools and update G2_SESSION_COOKIE in .env."
            )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = self._find_cards(soup)

        if not cards:
            logger.warning(
                "No review cards found for %s ★%d — run with --debug to inspect HTML",
                vendor["display"], stars,
            )

        for card in cards:
            company = self._extract_company(card)
            snippet = self._extract_snippet(card)
            rating = self._extract_rating(card) or stars
            review_url = self._extract_review_url(card)
            if company:
                yield {
                    "company": company,
                    "snippet": snippet,
                    "rating": rating,
                    "review_url": review_url,
                }

    def _find_cards(self, soup: BeautifulSoup) -> list:
        for sel in _REVIEW_CARD_SELECTORS:
            cards = soup.select(sel)
            if cards:
                logger.debug("Review cards found with selector: %s (%d cards)", sel, len(cards))
                return cards
        return []

    def _extract_company(self, card) -> str | None:
        for sel in _REVIEWER_TITLE_SELECTORS:
            el = card.select_one(sel)
            if el:
                text = el.get_text(" ", strip=True)
                m = _AT_COMPANY_RE.search(text)
                if m:
                    name = m.group(1).strip().rstrip(".,")
                    if len(name) >= 2 and name.lower() not in _NON_COMPANIES:
                        return name

        # Fallback: search all text in card for "at CompanyName"
        full_text = card.get_text(" ", strip=True)
        m = _AT_COMPANY_RE.search(full_text)
        if m:
            name = m.group(1).strip().rstrip(".,")
            if len(name) >= 2 and name.lower() not in _NON_COMPANIES:
                return name

        return None

    def _extract_snippet(self, card) -> str:
        for sel in _REVIEW_BODY_SELECTORS:
            el = card.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)[:500]
        return ""

    def _extract_rating(self, card) -> int | None:
        for sel in _STAR_SELECTORS:
            el = card.select_one(sel)
            if el:
                # itemprop="ratingValue" stores value as content attr or text
                val = el.get("content") or el.get("aria-label") or el.get_text(strip=True)
                m = re.search(r"(\d)", str(val))
                if m:
                    return int(m.group(1))
        return None

    def _extract_review_url(self, card) -> str:
        link = card.select_one("a[href*='/reviews/']")
        if link:
            href = link.get("href", "")
            return href if href.startswith("http") else f"https://www.g2.com{href}"
        return ""

    def _to_signal(self, review: dict, vendor_display: str) -> Signal:
        snippet = review.get("snippet", "")
        rating = review.get("rating")
        return Signal(
            signal_type="g2_review",
            company_name=review["company"],
            signal_strength=self._score(snippet, rating),
            source_url=review.get("review_url", ""),
            raw_data={
                "snippet": snippet,
                "rating": rating,
                "vendor": vendor_display,
            },
            metadata={
                "source_type": "g2_authenticated",
                "product_mentioned": vendor_display,
                "frustration_keywords": self._found_keywords(snippet),
                "star_rating": rating,
            },
        )

    def _score(self, text: str, rating: int | None) -> SignalStrength:
        lower = text.lower()
        for kw in _STRONG_KEYWORDS:
            if kw in lower:
                return SignalStrength.STRONG
        if rating is not None and rating <= 2:
            for kw in _MODERATE_KEYWORDS:
                if kw in lower:
                    return SignalStrength.STRONG
        for kw in _MODERATE_KEYWORDS:
            if kw in lower:
                return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def _found_keywords(self, text: str) -> list[str]:
        lower = text.lower()
        return [kw for kw in (_STRONG_KEYWORDS | _MODERATE_KEYWORDS) if kw in lower]


def scan(config: ScannerConfig) -> ScanResult:
    """Entry point called by scanner_runner."""
    return G2AuthenticatedScanner().scan(config.lookback_days)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="G2 authenticated review scanner")
    parser.add_argument("--debug", action="store_true", help="Save raw HTML for selector tuning")
    parser.add_argument("--lookback-days", type=int, default=30)
    args = parser.parse_args()

    scanner = G2AuthenticatedScanner(debug=args.debug)
    result = scanner.scan(args.lookback_days)
    print(f"\nG2 signals found: {len(result.signals_found)}")
    for s in result.signals_found:
        stars = s.metadata.get("star_rating", "?")
        vendor = s.raw_data.get("vendor", "?")
        print(f"  [{s.signal_strength.value}] {s.company_name} — {vendor} ★{stars}")
        if s.raw_data.get("snippet"):
            print(f"    \"{s.raw_data['snippet'][:120]}\"")
