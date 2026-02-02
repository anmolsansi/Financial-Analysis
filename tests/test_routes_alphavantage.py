"""Integration-style tests for Alpha Vantage routes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.routes import alphavantage
from app.services.alphavantage_service import (
    AuthError,
    InvalidSymbolError,
    RateLimitError,
    UpstreamError,
)


client = TestClient(app)


def _mock_service(method_name, return_value=None, side_effect=None):
    """Create a mock service object with an async method.

    Parameters:
        method_name: Name of the async method to mock.
        return_value: Value to return from the mock method.
        side_effect: Exception to raise from the mock method.

    Returns:
        SimpleNamespace: Mock service with configured method.

    Raises:
        None

    Edge Cases:
        side_effect is raised when the method is awaited.
    """
    mocked = SimpleNamespace()
    setattr(
        mocked,
        method_name,
        AsyncMock(return_value=return_value, side_effect=side_effect),
    )
    return mocked


def _mock_sync_service(method_name, return_value=None, side_effect=None):
    """Create a mock service object with a sync method.

    Parameters:
        method_name: Name of the method to mock.
        return_value: Value to return from the mock method.
        side_effect: Exception to raise from the mock method.

    Returns:
        SimpleNamespace: Mock service with configured method.

    Raises:
        None

    Edge Cases:
        side_effect is raised when the method is called.
    """
    def _handler(*args, **kwargs):
        if side_effect:
            raise side_effect
        return return_value

    mocked = SimpleNamespace()
    setattr(mocked, method_name, _handler)
    return mocked


def _make_daily_series_payload(days=40):
    """Build a synthetic daily series payload.

    Parameters:
        days: Number of days to include.

    Returns:
        dict: Daily series payload with sample data.

    Raises:
        None

    Edge Cases:
        Days less than 1 returns an empty series.
    """
    series = {}
    for i in range(days):
        date = f"2024-01-{31 - i:02d}"
        series[date] = {"4. close": str(100 + i)}
    return {"Time Series (Daily)": series}


def test_stock_price_success(monkeypatch):
    """Ensure stock price endpoint returns mock payload.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    mock_client = _mock_service("get_global_quote", return_value={"ok": True})
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/stock-price/AAPL")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_stock_price_invalid_format():
    """Ensure invalid symbols are rejected with 400.

    Parameters:
        None

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        Invalid characters trigger validation.
    """
    response = client.get("/api/stock-price/@@@")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid symbol format."


def test_stock_price_rate_limit(monkeypatch):
    """Ensure rate limits map to HTTP 429.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    mock_client = _mock_service(
        "get_global_quote",
        side_effect=RateLimitError("rate limit"),
    )
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/stock-price/AAPL")
    assert response.status_code == 429
    assert response.json()["detail"] == "rate limit"


def test_company_overview_auth_error(monkeypatch):
    """Ensure auth errors map to HTTP 401.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    mock_client = _mock_service(
        "get_company_overview",
        side_effect=AuthError("bad key"),
    )
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/company-overview/AAPL")
    assert response.status_code == 401
    assert response.json()["detail"] == "bad key"


def test_time_series_upstream_error(monkeypatch):
    """Ensure upstream errors map to HTTP 503.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    mock_client = _mock_service(
        "get_time_series_daily",
        side_effect=UpstreamError("upstream down"),
    )
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL")
    assert response.status_code == 503
    assert response.json()["detail"] == "upstream down"


def test_search_invalid_symbol_error(monkeypatch):
    """Ensure invalid symbol errors map to HTTP 404.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    mock_client = _mock_service(
        "search_symbol",
        side_effect=InvalidSymbolError("bad symbol"),
    )
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/app/search-symbol/tesla")
    assert response.status_code == 404
    assert response.json()["detail"] == "bad symbol"


def test_daily_last_7(monkeypatch):
    """Ensure last-7 endpoint returns 7 entries.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    payload = _make_daily_series_payload(days=20)
    mock_client = _mock_service("get_time_series_daily", return_value=payload)
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL/last-7")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert len(data["data"]) == 7


def test_daily_last_15(monkeypatch):
    """Ensure last-15 endpoint returns 15 entries.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    payload = _make_daily_series_payload(days=25)
    mock_client = _mock_service("get_time_series_daily", return_value=payload)
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL/last-15")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 15
    assert len(data["data"]) == 15


def test_daily_last_30(monkeypatch):
    """Ensure last-30 endpoint returns 30 entries.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    payload = _make_daily_series_payload(days=35)
    mock_client = _mock_service("get_time_series_daily", return_value=payload)
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL/last-30")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 30
    assert len(data["data"]) == 30


def test_daily_last_7_missing_series(monkeypatch):
    """Ensure missing daily series returns HTTP 502.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    mock_client = _mock_service("get_time_series_daily", return_value={})
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL/last-7")
    assert response.status_code == 502
    assert response.json()["detail"] == "Upstream daily series data missing."


def test_cached_quote_found(monkeypatch):
    """Ensure cached quote endpoint returns cached payload.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    cached = {
        "payload": {"Global Quote": {"01. symbol": "AAPL"}},
        "fetched_at": 123,
        "ttl_seconds": 600,
        "stale": False,
    }
    mock_client = _mock_sync_service(
        "get_cached_global_quote",
        return_value=cached,
    )
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/cache/quote/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["stale"] is False


def test_cached_quote_missing(monkeypatch):
    """Ensure missing cached quote returns HTTP 404.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    mock_client = _mock_sync_service(
        "get_cached_global_quote",
        return_value=None,
    )
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/cache/quote/AAPL")
    assert response.status_code == 404
    assert response.json()["detail"] == "No cached data found."


def test_cached_company_overview_found(monkeypatch):
    """Ensure cached company overview returns payload.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    cached = {
        "payload": {"Symbol": "AAPL"},
        "fetched_at": 456,
        "ttl_seconds": 86400,
        "stale": False,
    }
    mock_client = _mock_sync_service(
        "get_cached_company_overview",
        return_value=cached,
    )
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/cache/company-overview/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["stale"] is False


def test_cached_daily_missing(monkeypatch):
    """Ensure missing cached daily series returns HTTP 404.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None

    Raises:
        AssertionError: If response does not match expectations.

    Edge Cases:
        None
    """
    mock_client = _mock_sync_service(
        "get_cached_time_series_daily",
        return_value=None,
    )
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/cache/time-series/daily/AAPL")
    assert response.status_code == 404
    assert response.json()["detail"] == "No cached data found."
