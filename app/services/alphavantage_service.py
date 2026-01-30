import logging
import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SimpleCache:
    def __init__(self, ttl_seconds=120):
        self.ttl_seconds = ttl_seconds
        self._store = {}

    def get(self, key):
        entry = self._store.get(key)
        if not entry:
            return None
        value, ts = entry
        if time.monotonic() - ts > self.ttl_seconds:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key, value):
        self._store[key] = (value, time.monotonic())

class APIError(Exception):
    """Base exception for API-related failures."""
    pass

class RateLimitError(APIError):
    """Raised when the API rate limit is exceeded."""
    pass

class InvalidSymbolError(APIError):
    """Raised when a symbol or keyword is invalid."""
    pass

class AuthError(APIError):
    """Raised when API authentication fails."""
    pass

class UpstreamError(APIError):
    """Raised when the upstream service is unavailable or unstable."""
    pass

class AlphaVantageClient:
    BASE_URL = os.getenv("ALPHAVANTAGE_BASE_URL")

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided either as an argument or in the environment variables.")
        self._cache = SimpleCache(ttl_seconds=120)

    async def _make_request(self, params):
        params["apikey"] = self.api_key
        function = params.get("function", "UNKNOWN")
        cache_key = tuple(sorted(params.items()))
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("AlphaVantage cache hit: function=%s", function)
            return cached
        try:
            logger.info("AlphaVantage request start: function=%s params=%s", function, params)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
        except httpx.RequestError as e:
            logger.error("AlphaVantage request failed: function=%s error=%s", function, e)
            raise APIError(f"Network error: {e}") from e
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.error("AlphaVantage HTTP error: function=%s status=%s", function, status)
            if status in (401, 403):
                raise AuthError("Authentication failed with Alpha Vantage.") from e
            if status in (429, 500, 502, 503, 504):
                raise UpstreamError(f"Upstream error from Alpha Vantage (status {status}).") from e
            raise APIError(f"API request failed with status code {status}") from e

        data = response.json()

        if "Note" in data:
            logger.warning("AlphaVantage rate limit: function=%s note=%s", function, data["Note"])
            raise RateLimitError(data["Note"])

        if "Error Message" in data:
            logger.warning("AlphaVantage invalid symbol: function=%s error=%s", function, data["Error Message"])
            raise InvalidSymbolError(data["Error Message"])

        if "Information" in data:
            logger.warning("AlphaVantage info response: function=%s info=%s", function, data["Information"])
            raise APIError(data["Information"])

        if not data:
            logger.error("AlphaVantage empty response: function=%s", function)
            raise APIError("Empty response from Alpha Vantage.")

        self._cache.set(cache_key, data)
        logger.info("AlphaVantage request success: function=%s", function)
        return data

    async def get_time_series_daily(self, symbol):
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
        }
        return await self._make_request(params)
    
    async def get_time_series_weekly(self, symbol):
        params = {
            "function": "TIME_SERIES_WEEKLY",
            "symbol": symbol,
        }
        return await self._make_request(params)
    
    async def get_time_series_monthly(self, symbol):
        params = {
            "function": "TIME_SERIES_MONTHLY",
            "symbol": symbol,
        }
        return await self._make_request(params)
    
    async def get_global_quote(self, symbol):
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
        }
        return await self._make_request(params)
    
    async def search_symbol(self, keywords):
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords,
        }
        return await self._make_request(params)
    
    async def get_gold_spot_price(self):
        params = {
            "function": "GOLD_SILVER_SPOT",
            "symbol": "XAU",
        }
        return await self._make_request(params)
    
    async def get_silver_spot_price(self):
        params = {
            "function": "GOLD_SILVER_SPOT",
            "symbol": "XAG",
        }
        return await self._make_request(params)
    
    async def get_company_overview(self, symbol):
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
        }
        return await self._make_request(params)
    
    
    


    
