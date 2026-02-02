"""Alpha Vantage service client with caching and error handling."""

import logging
import json
import os
import time
import httpx
from dotenv import load_dotenv

from app.services.storage import SQLiteCache

load_dotenv()

logger = logging.getLogger(__name__)


class SimpleCache:
    """In-memory cache with TTL for short-lived responses.

    Parameters:
        ttl_seconds: Time-to-live for cached entries in seconds.

    Returns:
        None

    Raises:
        None

    Edge Cases:
        Expired entries are evicted on access.
    """

    def __init__(self, ttl_seconds=120):
        """Initialize the in-memory cache.

        Parameters:
            ttl_seconds: Time-to-live in seconds.

        Returns:
            None

        Raises:
            None

        Edge Cases:
            None
        """
        self.ttl_seconds = ttl_seconds
        self._store = {}

    def get(self, key):
        """Retrieve a cached value if present and not expired.

        Parameters:
            key: Cache key.

        Returns:
            Any | None: Cached value or None if missing/expired.

        Raises:
            None

        Edge Cases:
            Evicts and returns None for expired entries.
        """
        entry = self._store.get(key)
        if not entry:
            return None
        value, ts = entry
        if time.monotonic() - ts > self.ttl_seconds:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key, value):
        """Store a value in the cache with the current timestamp.

        Parameters:
            key: Cache key.
            value: Value to store.

        Returns:
            None

        Raises:
            None

        Edge Cases:
            Overwrites any existing entry with the same key.
        """
        self._store[key] = (value, time.monotonic())


class APIError(Exception):
    """Base exception for API-related failures.

    Parameters:
        None

    Returns:
        None

    Raises:
        None

    Edge Cases:
        Used as a generic catch-all for service errors.
    """
    pass


class RateLimitError(APIError):
    """Raised when the API rate limit is exceeded.

    Parameters:
        None

    Returns:
        None

    Raises:
        None

    Edge Cases:
        Triggered by Alpha Vantage "Note" responses.
    """
    pass


class InvalidSymbolError(APIError):
    """Raised when a symbol or keyword is invalid.

    Parameters:
        None

    Returns:
        None

    Raises:
        None

    Edge Cases:
        Triggered by Alpha Vantage "Error Message" responses.
    """
    pass


class AuthError(APIError):
    """Raised when API authentication fails.

    Parameters:
        None

    Returns:
        None

    Raises:
        None

    Edge Cases:
        Raised on HTTP 401/403 responses.
    """
    pass


class UpstreamError(APIError):
    """Raised when the upstream service is unavailable or unstable.

    Parameters:
        None

    Returns:
        None

    Raises:
        None

    Edge Cases:
        Raised on HTTP 429/5xx responses.
    """
    pass


class AlphaVantageClient:
    """Async client for Alpha Vantage with layered caching.

    Parameters:
        api_key: API key string. Falls back to environment variable.
        db_path: Optional SQLite cache path.

    Returns:
        None

    Raises:
        ValueError: If no API key is provided.

    Edge Cases:
        Uses environment variables when parameters are omitted.
    """

    BASE_URL = os.getenv("ALPHAVANTAGE_BASE_URL")

    def __init__(self, api_key=None, db_path=None):
        """Initialize the client with in-memory and SQLite caches.

        Parameters:
            api_key: API key string.
            db_path: Optional SQLite cache path.

        Returns:
            None

        Raises:
            ValueError: If no API key is provided.

        Edge Cases:
            Uses default DB path when not provided.
        """
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided either as an argument or in the "
                "environment variables."
            )
        self._cache = SimpleCache(ttl_seconds=120)
        storage_path = db_path or os.getenv(
            "ALPHAVANTAGE_DB_PATH",
            os.path.join("data", "alphavantage_cache.db"),
        )
        self._store = SQLiteCache(storage_path)

    def _build_cache_key(self, function, params):
        """Build a stable cache key excluding the API key.

        Parameters:
            function: Alpha Vantage function name.
            params: Request parameters.

        Returns:
            str: Deterministic cache key.

        Raises:
            None

        Edge Cases:
            Parameter ordering is normalized via JSON sorting.
        """
        safe_params = {k: v for k, v in params.items() if k != "apikey"}
        return f"{function}:{json.dumps(safe_params, sort_keys=True)}"

    def _get_cached(self, function, params, allow_stale=False):
        """Lookup cached data from SQLite.

        Parameters:
            function: Alpha Vantage function name.
            params: Request parameters.
            allow_stale: If True, return stale cache entries.

        Returns:
            dict | None: Cached payload metadata or None if missing/expired.

        Raises:
            None

        Edge Cases:
            Returns None if entry is stale and allow_stale is False.
        """
        cache_key = self._build_cache_key(function, params)
        cached = self._store.get(cache_key, allow_stale=allow_stale)
        if not cached:
            return None
        return cached

    async def _make_request(self, params, ttl_seconds=None):
        """Execute an API request with caching and error handling.

        Parameters:
            params: Request parameters for Alpha Vantage.
            ttl_seconds: Optional TTL for SQLite cache storage.

        Returns:
            dict: Parsed JSON response.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            InvalidSymbolError: When a symbol is invalid.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            Falls back to cached responses when available.
        """
        params["apikey"] = self.api_key
        function = params.get("function", "UNKNOWN")
        cache_key = tuple(sorted(params.items()))
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("AlphaVantage cache hit: function=%s", function)
            return cached
        cached = self._get_cached(function, params)
        if cached is not None:
            logger.info("AlphaVantage DB cache hit: function=%s", function)
            return cached["payload"]
        try:
            logger.info(
                "AlphaVantage request start: function=%s params=%s",
                function,
                params,
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
        except httpx.RequestError as e:
            logger.error(
                "AlphaVantage request failed: function=%s error=%s",
                function,
                e,
            )
            raise APIError(f"Network error: {e}") from e
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.error(
                "AlphaVantage HTTP error: function=%s status=%s",
                function,
                status,
            )
            if status in (401, 403):
                raise AuthError("Authentication failed with Alpha Vantage.") from e
            if status in (429, 500, 502, 503, 504):
                raise UpstreamError(
                    f"Upstream error from Alpha Vantage (status {status})."
                ) from e
            raise APIError(f"API request failed with status code {status}") from e

        data = response.json()

        if "Note" in data:
            logger.warning(
                "AlphaVantage rate limit: function=%s note=%s",
                function,
                data["Note"],
            )
            raise RateLimitError(data["Note"])

        if "Error Message" in data:
            logger.warning(
                "AlphaVantage invalid symbol: function=%s error=%s",
                function,
                data["Error Message"],
            )
            raise InvalidSymbolError(data["Error Message"])

        if "Information" in data:
            logger.warning(
                "AlphaVantage info response: function=%s info=%s",
                function,
                data["Information"],
            )
            raise APIError(data["Information"])

        if not data:
            logger.error("AlphaVantage empty response: function=%s", function)
            raise APIError("Empty response from Alpha Vantage.")

        self._cache.set(cache_key, data)
        if ttl_seconds is not None:
            db_cache_key = self._build_cache_key(function, params)
            self._store.save(
                db_cache_key,
                data,
                ttl_seconds=ttl_seconds,
                endpoint=function,
            )
        logger.info("AlphaVantage request success: function=%s", function)
        return data

    async def get_time_series_daily(self, symbol):
        """Fetch daily time series data for a symbol.

        Parameters:
            symbol: Stock symbol.

        Returns:
            dict: API response payload.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            InvalidSymbolError: When a symbol is invalid.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            Uses 10-minute SQLite TTL.
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
        }
        return await self._make_request(params, ttl_seconds=600)

    async def get_time_series_weekly(self, symbol):
        """Fetch weekly time series data for a symbol.

        Parameters:
            symbol: Stock symbol.

        Returns:
            dict: API response payload.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            InvalidSymbolError: When a symbol is invalid.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            None
        """
        params = {
            "function": "TIME_SERIES_WEEKLY",
            "symbol": symbol,
        }
        return await self._make_request(params)

    async def get_time_series_monthly(self, symbol):
        """Fetch monthly time series data for a symbol.

        Parameters:
            symbol: Stock symbol.

        Returns:
            dict: API response payload.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            InvalidSymbolError: When a symbol is invalid.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            None
        """
        params = {
            "function": "TIME_SERIES_MONTHLY",
            "symbol": symbol,
        }
        return await self._make_request(params)

    async def get_global_quote(self, symbol):
        """Fetch the latest quote for a symbol.

        Parameters:
            symbol: Stock symbol.

        Returns:
            dict: API response payload.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            InvalidSymbolError: When a symbol is invalid.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            Uses 10-minute SQLite TTL.
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
        }
        return await self._make_request(params, ttl_seconds=600)

    async def search_symbol(self, keywords):
        """Search for symbols using keywords.

        Parameters:
            keywords: Search keywords.

        Returns:
            dict: API response payload.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            InvalidSymbolError: When a symbol is invalid.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            None
        """
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords,
        }
        return await self._make_request(params)

    async def get_gold_spot_price(self):
        """Fetch gold spot price data.

        Parameters:
            None

        Returns:
            dict: API response payload.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            None
        """
        params = {
            "function": "GOLD_SILVER_SPOT",
            "symbol": "XAU",
        }
        return await self._make_request(params)

    async def get_silver_spot_price(self):
        """Fetch silver spot price data.

        Parameters:
            None

        Returns:
            dict: API response payload.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            None
        """
        params = {
            "function": "GOLD_SILVER_SPOT",
            "symbol": "XAG",
        }
        return await self._make_request(params)

    async def get_company_overview(self, symbol):
        """Fetch company overview data for a symbol.

        Parameters:
            symbol: Stock symbol.

        Returns:
            dict: API response payload.

        Raises:
            APIError: For network or response format errors.
            RateLimitError: When API rate limits are hit.
            InvalidSymbolError: When a symbol is invalid.
            AuthError: When authentication fails.
            UpstreamError: For upstream 5xx/429 issues.

        Edge Cases:
            Uses 1-day SQLite TTL.
        """
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
        }
        return await self._make_request(params, ttl_seconds=86400)

    def get_cached_time_series_daily(self, symbol, allow_stale=False):
        """Retrieve cached daily time series data from SQLite.

        Parameters:
            symbol: Stock symbol.
            allow_stale: If True, return stale cache entries.

        Returns:
            dict | None: Cached payload metadata or None.

        Raises:
            None

        Edge Cases:
            Returns None if cache entry is missing or expired.
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
        }
        return self._get_cached("TIME_SERIES_DAILY", params, allow_stale=allow_stale)

    def get_cached_global_quote(self, symbol, allow_stale=False):
        """Retrieve cached global quote data from SQLite.

        Parameters:
            symbol: Stock symbol.
            allow_stale: If True, return stale cache entries.

        Returns:
            dict | None: Cached payload metadata or None.

        Raises:
            None

        Edge Cases:
            Returns None if cache entry is missing or expired.
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
        }
        return self._get_cached("GLOBAL_QUOTE", params, allow_stale=allow_stale)

    def get_cached_company_overview(self, symbol, allow_stale=False):
        """Retrieve cached company overview data from SQLite.

        Parameters:
            symbol: Stock symbol.
            allow_stale: If True, return stale cache entries.

        Returns:
            dict | None: Cached payload metadata or None.

        Raises:
            None

        Edge Cases:
            Returns None if cache entry is missing or expired.
        """
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
        }
        return self._get_cached("OVERVIEW", params, allow_stale=allow_stale)
