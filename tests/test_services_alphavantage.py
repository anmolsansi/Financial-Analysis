"""Unit tests for the Alpha Vantage service layer."""

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
    """Create an httpx.Response for testing.

    Parameters:
        status_code: HTTP status code.
        json_data: JSON payload to include.

    Returns:
        httpx.Response: Configured response object.

    Raises:
        None

    Edge Cases:
        Allows empty payloads via json_data=None.
    """
    request = httpx.Request("GET", "https://example.com")
    return httpx.Response(status_code, json=json_data, request=request)


class _FakeAsyncClient:
    """Async client stub for mocking httpx.AsyncClient.

    Parameters:
        None

    Returns:
        None

    Raises:
        None

    Edge Cases:
        Can be configured to raise exceptions on get().
    """

    def __init__(self, response=None, exc=None):
        """Initialize the fake client.

        Parameters:
            response: Response to return.
            exc: Optional exception to raise.
        Returns:
            None

        Raises:
            None

        Edge Cases:
            When exc is provided, get() will raise it.
        """
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        """Enter async context manager.

        Returns:
            _FakeAsyncClient: The instance itself.

        Raises:
            None

        Edge Cases:
            None
        """
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit async context manager.

        Parameters:
            exc_type: Exception type if raised.
            exc: Exception instance if raised.
            tb: Traceback if raised.

        Returns:
            bool: False to propagate exceptions.

        Raises:
            None

        Edge Cases:
            Always returns False to avoid suppressing errors.
        """
        return False

    async def get(self, url, params=None):
        """Return a response or raise an exception.

        Parameters:
            url: Request URL.
            params: Query parameters.

        Returns:
            httpx.Response: Configured response.

        Raises:
            Exception: If exc was provided at init.

        Edge Cases:
            Returns the preconfigured response regardless of URL.
        """
        if self._exc:
            raise self._exc
        return self._response


def _patch_async_client(monkeypatch, response=None, exc=None):
    """Patch httpx.AsyncClient with a fake client.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.
        response: Response to return from fake client.
        exc: Optional exception to raise from fake client.

    Returns:
        None

    Raises:
        None

    Edge Cases:
        Overrides AsyncClient for the duration of the test.
    """
    monkeypatch.setattr(
        alphavantage_service.httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response=response, exc=exc),
    )


def _make_client(tmp_path):
    """Create a client instance with a temp SQLite cache.

    Parameters:
        tmp_path: Pytest temporary directory path.

    Returns:
        AlphaVantageClient: Configured client instance.

    Raises:
        None

    Edge Cases:
        Uses a unique DB per test run.
    """
    db_path = tmp_path / "alpha_cache.db"
    return AlphaVantageClient(api_key="test", db_path=str(db_path))


def test_get_global_quote_success(monkeypatch, tmp_path):
    """Verify successful global quote fetch returns payload.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary path fixture.

    Returns:
        None

    Raises:
        AssertionError: If assertions fail.

    Edge Cases:
        None
    """
    AlphaVantageClient.BASE_URL = "https://example.com"
    payload = {"Global Quote": {"01. symbol": "AAPL"}}
    response = _make_response(json_data=payload)
    _patch_async_client(monkeypatch, response=response)

    client = _make_client(tmp_path)
    result = asyncio.run(client.get_global_quote("AAPL"))

    assert result == payload


def test_rate_limit_error(monkeypatch, tmp_path):
    """Verify rate limit response raises RateLimitError.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary path fixture.

    Returns:
        None

    Raises:
        RateLimitError: Expected from client call.
        AssertionError: If error is not raised.

    Edge Cases:
        None
    """
    AlphaVantageClient.BASE_URL = "https://example.com"
    payload = {"Note": "Too many requests."}
    response = _make_response(json_data=payload)
    _patch_async_client(monkeypatch, response=response)

    client = _make_client(tmp_path)
    with pytest.raises(RateLimitError):
        asyncio.run(client.get_global_quote("AAPL"))


def test_invalid_symbol_error(monkeypatch, tmp_path):
    """Verify invalid symbol response raises InvalidSymbolError.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary path fixture.

    Returns:
        None

    Raises:
        InvalidSymbolError: Expected from client call.
        AssertionError: If error is not raised.

    Edge Cases:
        None
    """
    AlphaVantageClient.BASE_URL = "https://example.com"
    payload = {"Error Message": "Invalid API call."}
    response = _make_response(json_data=payload)
    _patch_async_client(monkeypatch, response=response)

    client = _make_client(tmp_path)
    with pytest.raises(InvalidSymbolError):
        asyncio.run(client.get_global_quote("BAD"))


def test_auth_error_on_401(monkeypatch, tmp_path):
    """Verify 401 response raises AuthError.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary path fixture.

    Returns:
        None

    Raises:
        AuthError: Expected from client call.
        AssertionError: If error is not raised.

    Edge Cases:
        None
    """
    AlphaVantageClient.BASE_URL = "https://example.com"
    response = _make_response(status_code=401, json_data={"error": "nope"})
    _patch_async_client(monkeypatch, response=response)

    client = _make_client(tmp_path)
    with pytest.raises(AuthError):
        asyncio.run(client.get_global_quote("AAPL"))


def test_upstream_error_on_503(monkeypatch, tmp_path):
    """Verify 503 response raises UpstreamError.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary path fixture.

    Returns:
        None

    Raises:
        UpstreamError: Expected from client call.
        AssertionError: If error is not raised.

    Edge Cases:
        None
    """
    AlphaVantageClient.BASE_URL = "https://example.com"
    response = _make_response(status_code=503, json_data={"error": "down"})
    _patch_async_client(monkeypatch, response=response)

    client = _make_client(tmp_path)
    with pytest.raises(UpstreamError):
        asyncio.run(client.get_global_quote("AAPL"))


def test_empty_response_error(monkeypatch, tmp_path):
    """Verify empty payload raises APIError.

    Parameters:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary path fixture.

    Returns:
        None

    Raises:
        APIError: Expected from client call.
        AssertionError: If error is not raised.

    Edge Cases:
        None
    """
    AlphaVantageClient.BASE_URL = "https://example.com"
    response = _make_response(json_data={})
    _patch_async_client(monkeypatch, response=response)

    client = _make_client(tmp_path)
    with pytest.raises(APIError):
        asyncio.run(client.get_global_quote("AAPL"))
