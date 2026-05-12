"""Unit tests for G2 Review Scanner.

Detects companies expressing frustration with Marketo or HubSpot via G2 reviews.
A VP Marketing leaving a negative G2 review is a high-intent migration signal.

All HTTP calls are mocked — no real network requests.
"""

from unittest.mock import MagicMock, patch
from scripts.scanners.g2_scanner import G2ReviewScanner, scan
from scripts.config_loader import ScannerConfig
from scripts.models import SignalStrength


SAMPLE_G2_RESULT = {
    "title": "Marketo Review: Too Complex After Adobe — VP Marketing at Acme Corp",
    "url": "https://www.g2.com/products/marketo-engage/reviews/marketo-engage-review-12345",
    "snippet": "We've been on Marketo for 3 years and the complexity after the Adobe acquisition "
               "has made simple tasks feel like filing taxes. We're evaluating alternatives.",
    "company": None,
}

SAMPLE_HUBSPOT_RESULT = {
    "title": "HubSpot Enterprise Review — at Beta Inc",
    "url": "https://www.g2.com/products/hubspot-marketing-hub/reviews/hubspot-1234",
    "snippet": "HubSpot Enterprise doesn't talk to our Snowflake warehouse without a lot of duct tape.",
    "company": None,
}

NON_G2_RESULT = {
    "title": "Marketo vs Alternatives",
    "url": "https://www.capterra.com/marketing-software/",
    "snippet": "Compare marketing automation tools.",
    "company": None,
}


def test_g2_scanner_creates_signals_from_results():
    """G2 scanner should convert G2 review results into signals."""
    scanner = G2ReviewScanner(api_key="fake-key")
    with patch.object(scanner._client, "search_jobs", return_value=[SAMPLE_G2_RESULT]):
        result = scanner.scan(lookback_days=7)
    assert len(result.signals_found) > 0
    assert all(s.signal_type == "g2_review_frustration" for s in result.signals_found)


def test_g2_scanner_filters_non_g2_urls():
    """Scanner must skip results that are not from g2.com."""
    scanner = G2ReviewScanner(api_key="fake-key")
    with patch.object(scanner._client, "search_jobs", return_value=[NON_G2_RESULT]):
        result = scanner.scan(lookback_days=7)
    assert len(result.signals_found) == 0


def test_g2_scanner_marks_migration_language_as_strong():
    """Review containing 'evaluating alternatives' should produce STRONG signal."""
    scanner = G2ReviewScanner(api_key="fake-key")
    with patch.object(scanner._client, "search_jobs", return_value=[SAMPLE_G2_RESULT]):
        result = scanner.scan(lookback_days=7)
    assert any(s.signal_strength == SignalStrength.STRONG for s in result.signals_found)


def test_g2_scanner_no_api_key_returns_empty_with_no_crash():
    """Without API key, scanner should return 0 signals without crashing."""
    from scripts.config import AppConfig

    fake_config = AppConfig(serpapi_key=None)
    with patch("scripts.config.get_config", return_value=fake_config):
        scanner = G2ReviewScanner(api_key=None)
        # Client returns [] when no key — scanner should handle gracefully
        result = scanner.scan(lookback_days=7)
    assert result.scan_type == "g2_review_frustration"
    assert len(result.signals_found) == 0


def test_scan_module_function_uses_config():
    """Module-level scan() should accept ScannerConfig and return correct scan_type."""
    cfg = ScannerConfig(
        enabled=True,
        module="scripts.scanners.g2_scanner",
        keywords=["Marketo", "HubSpot"],
        lookback_days=7,
    )
    with patch("scripts.scanners.g2_scanner.G2ReviewScanner.scan", return_value=MagicMock(scan_type="g2_review_frustration")):
        result = scan(cfg)
    assert result.scan_type == "g2_review_frustration"
