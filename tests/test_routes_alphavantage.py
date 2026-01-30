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
    mocked = SimpleNamespace()
    setattr(
        mocked,
        method_name,
        AsyncMock(return_value=return_value, side_effect=side_effect),
    )
    return mocked


def _make_daily_series_payload(days=40):
    series = {}
    for i in range(days):
        date = f"2024-01-{31 - i:02d}"
        series[date] = {"4. close": str(100 + i)}
    return {"Time Series (Daily)": series}


def test_stock_price_success(monkeypatch):
    mock_client = _mock_service("get_global_quote", return_value={"ok": True})
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/stock-price/AAPL")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_stock_price_invalid_format():
    response = client.get("/api/stock-price/@@@")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid symbol format."


def test_stock_price_rate_limit(monkeypatch):
    mock_client = _mock_service("get_global_quote", side_effect=RateLimitError("rate limit"))
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/stock-price/AAPL")
    assert response.status_code == 429
    assert response.json()["detail"] == "rate limit"


def test_company_overview_auth_error(monkeypatch):
    mock_client = _mock_service("get_company_overview", side_effect=AuthError("bad key"))
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/company-overview/AAPL")
    assert response.status_code == 401
    assert response.json()["detail"] == "bad key"


def test_time_series_upstream_error(monkeypatch):
    mock_client = _mock_service("get_time_series_daily", side_effect=UpstreamError("upstream down"))
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL")
    assert response.status_code == 503
    assert response.json()["detail"] == "upstream down"


def test_search_invalid_symbol_error(monkeypatch):
    mock_client = _mock_service("search_symbol", side_effect=InvalidSymbolError("bad symbol"))
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/app/search-symbol/tesla")
    assert response.status_code == 404
    assert response.json()["detail"] == "bad symbol"


def test_daily_last_7(monkeypatch):
    payload = _make_daily_series_payload(days=20)
    mock_client = _mock_service("get_time_series_daily", return_value=payload)
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL/last-7")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert len(data["data"]) == 7


def test_daily_last_15(monkeypatch):
    payload = _make_daily_series_payload(days=25)
    mock_client = _mock_service("get_time_series_daily", return_value=payload)
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL/last-15")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 15
    assert len(data["data"]) == 15


def test_daily_last_30(monkeypatch):
    payload = _make_daily_series_payload(days=35)
    mock_client = _mock_service("get_time_series_daily", return_value=payload)
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL/last-30")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 30
    assert len(data["data"]) == 30


def test_daily_last_7_missing_series(monkeypatch):
    mock_client = _mock_service("get_time_series_daily", return_value={})
    monkeypatch.setattr(alphavantage, "client", mock_client)

    response = client.get("/api/time-series/daily/AAPL/last-7")
    assert response.status_code == 502
    assert response.json()["detail"] == "Upstream daily series data missing."
