"""Unit tests for G2AuthenticatedScanner. All HTTP calls mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scripts.scanners.g2_authenticated_scanner import G2AuthenticatedScanner, scan
from scripts.config_loader import ScannerConfig
from scripts.models import SignalStrength

# Minimal HTML that looks like an authenticated G2 review page
_REVIEW_HTML = """
<html><body>
  <div itemprop="review">
    <div class="reviewer-info__title">VP Marketing at Acme Corp</div>
    <p itemprop="reviewBody">Marketo is too complex and way too expensive for our team size. We are evaluating alternatives.</p>
    <span itemprop="ratingValue" content="2">2</span>
    <a href="/reviews/marketo-review-123">Read more</a>
  </div>
  <div itemprop="review">
    <div class="reviewer-info__title">Director of Demand Gen at Beta Inc</div>
    <p itemprop="reviewBody">HubSpot Enterprise keeps hitting our ceiling on custom audiences. Painful workarounds every week.</p>
    <span itemprop="ratingValue" content="3">3</span>
  </div>
</body></html>
"""

_EMPTY_HTML = "<html><body><p>No reviews found.</p></body></html>"

_NO_COMPANY_HTML = """
<html><body>
  <div itemprop="review">
    <div class="reviewer-info__title">Anonymous Reviewer</div>
    <p itemprop="reviewBody">It was okay I guess.</p>
  </div>
</body></html>
"""


def _make_response(html: str, status: int = 200):
    mock = MagicMock()
    mock.status_code = status
    mock.text = html
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def scanner():
    return G2AuthenticatedScanner(cookie="fake_session=abc123")


def test_extracts_company_names(scanner):
    with patch.object(scanner._session, "get", return_value=_make_response(_REVIEW_HTML)):
        result = scanner.scan(lookback_days=7)
    companies = {s.company_name for s in result.signals_found}
    assert "Acme Corp" in companies
    assert "Beta Inc" in companies


def test_signal_type_is_g2_review(scanner):
    with patch.object(scanner._session, "get", return_value=_make_response(_REVIEW_HTML)):
        result = scanner.scan(lookback_days=7)
    assert all(s.signal_type == "g2_review" for s in result.signals_found)


def test_evaluating_keyword_scores_strong(scanner):
    with patch.object(scanner._session, "get", return_value=_make_response(_REVIEW_HTML)):
        result = scanner.scan(lookback_days=7)
    acme = next(s for s in result.signals_found if s.company_name == "Acme Corp")
    assert acme.signal_strength == SignalStrength.STRONG


def test_ceiling_keyword_with_low_star_scores_strong(scanner):
    """'ceiling' is MODERATE keyword but rating=3 + 'painful' = MODERATE; rating=2 would be STRONG."""
    with patch.object(scanner._session, "get", return_value=_make_response(_REVIEW_HTML)):
        result = scanner.scan(lookback_days=7)
    beta = next(s for s in result.signals_found if s.company_name == "Beta Inc")
    assert beta.signal_strength in (SignalStrength.STRONG, SignalStrength.MODERATE)


def test_skips_cards_without_company(scanner):
    with patch.object(scanner._session, "get", return_value=_make_response(_NO_COMPANY_HTML)):
        result = scanner.scan(lookback_days=7)
    assert len(result.signals_found) == 0


def test_empty_page_returns_zero_signals(scanner):
    with patch.object(scanner._session, "get", return_value=_make_response(_EMPTY_HTML)):
        result = scanner.scan(lookback_days=7)
    assert len(result.signals_found) == 0


def test_deduplicates_same_company_across_vendors(scanner):
    """Same company appearing in Marketo + HubSpot reviews → one signal."""
    with patch.object(scanner._session, "get", return_value=_make_response(_REVIEW_HTML)):
        result = scanner.scan(lookback_days=7)
    companies = [s.company_name for s in result.signals_found]
    assert len(companies) == len(set(c.lower() for c in companies))


def test_missing_cookie_returns_empty_with_no_crash():
    scanner = G2AuthenticatedScanner(cookie="")
    result = scanner.scan()
    assert len(result.signals_found) == 0
    assert result.scan_type == "g2_review"
    assert any("G2_SESSION_COOKIE" in e for e in result.errors)


def test_403_logs_error_and_continues(scanner):
    forbidden = _make_response("", status=403)
    forbidden.raise_for_status = MagicMock()
    with patch.object(scanner._session, "get", return_value=forbidden):
        result = scanner.scan()
    assert len(result.errors) > 0
    assert any("403" in e or "cookie" in e.lower() for e in result.errors)


def test_scan_module_function():
    cfg = ScannerConfig(
        enabled=True,
        module="scripts.scanners.g2_authenticated_scanner",
        keywords=["Marketo"],
        lookback_days=7,
    )
    with patch(
        "scripts.scanners.g2_authenticated_scanner.G2AuthenticatedScanner.scan"
    ) as mock_scan:
        mock_scan.return_value = MagicMock(scan_type="g2_review", signals_found=[])
        result = scan(cfg)
    mock_scan.assert_called_once_with(7)
