import asyncio

import httpx
import pytest

from app.services import alphavantage_service
from app.services.alphavantage_service import (
    AlphaVantageClient,
    APIError,
    AuthError,
    InvalidSymbolError,
    RateLimitError,
    UpstreamError,
)


def _make_response(status_code=200, json_data=None):
    request = httpx.Request("GET", "https://example.com")
    return httpx.Response(status_code, json=json_data, request=request)


class _FakeAsyncClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        if self._exc:
            raise self._exc
        return self._response


def _patch_async_client(monkeypatch, response=None, exc=None):
    monkeypatch.setattr(
        alphavantage_service.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response=response, exc=exc),
    )


def test_get_global_quote_success(monkeypatch):
    AlphaVantageClient.BASE_URL = "https://example.com"
    payload = {"Global Quote": {"01. symbol": "AAPL"}}
    response = _make_response(json_data=payload)
    _patch_async_client(monkeypatch, response=response)

    client = AlphaVantageClient(api_key="test")
    result = asyncio.run(client.get_global_quote("AAPL"))

    assert result == payload


def test_rate_limit_error(monkeypatch):
    AlphaVantageClient.BASE_URL = "https://example.com"
    payload = {"Note": "Too many requests."}
    response = _make_response(json_data=payload)
    _patch_async_client(monkeypatch, response=response)

    client = AlphaVantageClient(api_key="test")
    with pytest.raises(RateLimitError):
        asyncio.run(client.get_global_quote("AAPL"))


def test_invalid_symbol_error(monkeypatch):
    AlphaVantageClient.BASE_URL = "https://example.com"
    payload = {"Error Message": "Invalid API call."}
    response = _make_response(json_data=payload)
    _patch_async_client(monkeypatch, response=response)

    client = AlphaVantageClient(api_key="test")
    with pytest.raises(InvalidSymbolError):
        asyncio.run(client.get_global_quote("BAD"))


def test_auth_error_on_401(monkeypatch):
    AlphaVantageClient.BASE_URL = "https://example.com"
    response = _make_response(status_code=401, json_data={"error": "nope"})
    _patch_async_client(monkeypatch, response=response)

    client = AlphaVantageClient(api_key="test")
    with pytest.raises(AuthError):
        asyncio.run(client.get_global_quote("AAPL"))


def test_upstream_error_on_503(monkeypatch):
    AlphaVantageClient.BASE_URL = "https://example.com"
    response = _make_response(status_code=503, json_data={"error": "down"})
    _patch_async_client(monkeypatch, response=response)

    client = AlphaVantageClient(api_key="test")
    with pytest.raises(UpstreamError):
        asyncio.run(client.get_global_quote("AAPL"))


def test_empty_response_error(monkeypatch):
    AlphaVantageClient.BASE_URL = "https://example.com"
    response = _make_response(json_data={})
    _patch_async_client(monkeypatch, response=response)

    client = AlphaVantageClient(api_key="test")
    with pytest.raises(APIError):
        asyncio.run(client.get_global_quote("AAPL"))
