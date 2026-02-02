"""API routes for Alpha Vantage-backed data endpoints."""

from fastapi import APIRouter, HTTPException, Query
from app.services.alphavantage_service import (
    AlphaVantageClient,
    APIError,
    RateLimitError,
    InvalidSymbolError,
    AuthError,
    UpstreamError,
)

router = APIRouter()
client = AlphaVantageClient()


def _validate_symbol(symbol: str):
    """Validate a symbol path parameter.

    Parameters:
        symbol: Stock symbol string.

    Returns:
        None

    Raises:
        HTTPException: If the symbol is missing or malformed.

    Edge Cases:
        Rejects symbols with unsupported characters.
    """
    if not symbol or len(symbol) > 10 or not symbol.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid symbol format.")


def _validate_keywords(keywords: str):
    """Validate search keywords.

    Parameters:
        keywords: Search keywords string.

    Returns:
        None

    Raises:
        HTTPException: If keywords are empty or too long.

    Edge Cases:
        Rejects overly long keyword strings.
    """
    if not keywords or len(keywords) > 50:
        raise HTTPException(status_code=400, detail="Invalid keywords.")


def _extract_daily_series(payload: dict) -> dict:
    """Extract the daily time series from a payload.

    Parameters:
        payload: API response payload.

    Returns:
        dict: Daily time series mapping by date.

    Raises:
        HTTPException: If the series data is missing or invalid.

    Edge Cases:
        Raises when payload lacks expected Alpha Vantage keys.
    """
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise HTTPException(
            status_code=502,
            detail="Upstream daily series data missing.",
        )
    return series


def _filter_last_days(series: dict, days: int) -> dict:
    """Select the most recent N entries from a daily series.

    Parameters:
        series: Mapping of date strings to data points.
        days: Number of most recent days to return.

    Returns:
        dict: Filtered series limited to the most recent days.

    Raises:
        None

    Edge Cases:
        Returns fewer entries if series has less than N items.
    """
    dates = sorted(series.keys(), reverse=True)
    recent_dates = dates[:days]
    return {date: series[date] for date in recent_dates}


def _handle_error(error: Exception):
    """Translate service errors to HTTP responses.

    Parameters:
        error: Exception raised by route or service logic.

    Returns:
        None

    Raises:
        HTTPException: With appropriate status codes and messages.

    Edge Cases:
        Passthrough when error is already an HTTPException.
    """
    if isinstance(error, HTTPException):
        raise error
    if isinstance(error, InvalidSymbolError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, RateLimitError):
        raise HTTPException(status_code=429, detail=str(error))
    if isinstance(error, AuthError):
        raise HTTPException(status_code=401, detail=str(error))
    if isinstance(error, UpstreamError):
        raise HTTPException(status_code=503, detail=str(error))
    if isinstance(error, APIError):
        raise HTTPException(status_code=500, detail=str(error))
    raise HTTPException(status_code=500, detail="Unexpected server error")


@router.get("/stock-price/{symbol}")
async def get_stock_price(symbol: str):
    """Return the latest global quote for a symbol.

    Parameters:
        symbol: Stock symbol.

    Returns:
        dict: Quote payload from Alpha Vantage.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Rate limits return HTTP 429.
    """
    try:
        _validate_symbol(symbol)
        data = await client.get_global_quote(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/app/search-symbol/{keywords}")
async def search_symbol(keywords: str):
    """Search for symbols using keywords.

    Parameters:
        keywords: Search keywords.

    Returns:
        dict: Search results payload.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Empty keywords return HTTP 400.
    """
    try:
        _validate_keywords(keywords)
        data = await client.search_symbol(keywords)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/daily/{symbol}")
async def time_series_daily(symbol: str):
    """Return daily time series data for a symbol.

    Parameters:
        symbol: Stock symbol.

    Returns:
        dict: Daily time series payload.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Upstream format changes return HTTP 502.
    """
    try:
        _validate_symbol(symbol)
        data = await client.get_time_series_daily(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/weekly/{symbol}")
async def time_series_weekly(symbol: str):
    """Return weekly time series data for a symbol.

    Parameters:
        symbol: Stock symbol.

    Returns:
        dict: Weekly time series payload.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Upstream errors return HTTP 503.
    """
    try:
        _validate_symbol(symbol)
        data = await client.get_time_series_weekly(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/monthly/{symbol}")
async def time_series_monthly(symbol: str):
    """Return monthly time series data for a symbol.

    Parameters:
        symbol: Stock symbol.

    Returns:
        dict: Monthly time series payload.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Upstream errors return HTTP 503.
    """
    try:
        _validate_symbol(symbol)
        data = await client.get_time_series_monthly(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/gold-spot-price")
async def gold_spot_price():
    """Return the gold spot price payload.

    Returns:
        dict: Gold spot price payload.

    Raises:
        HTTPException: For upstream errors.

    Edge Cases:
        Rate limits return HTTP 429.
    """
    try:
        data = await client.get_gold_spot_price()
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/silver-spot-price")
async def silver_spot_price():
    """Return the silver spot price payload.

    Returns:
        dict: Silver spot price payload.

    Raises:
        HTTPException: For upstream errors.

    Edge Cases:
        Rate limits return HTTP 429.
    """
    try:
        data = await client.get_silver_spot_price()
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/company-overview/{symbol}")
async def company_overview(symbol: str):
    """Return company overview data for a symbol.

    Parameters:
        symbol: Stock symbol.

    Returns:
        dict: Company overview payload.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Missing symbols return HTTP 404.
    """
    try:
        _validate_symbol(symbol)
        data = await client.get_company_overview(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/daily/{symbol}/last-7")
async def time_series_daily_last_7(symbol: str):
    """Return the most recent 7 days of daily data for a symbol.

    Parameters:
        symbol: Stock symbol.

    Returns:
        dict: Filtered daily series with metadata.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Returns fewer than 7 entries if data is sparse.
    """
    try:
        _validate_symbol(symbol)
        payload = await client.get_time_series_daily(symbol)
        series = _extract_daily_series(payload)
        return {
            "symbol": symbol.upper(),
            "days": 7,
            "data": _filter_last_days(series, 7),
        }
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/daily/{symbol}/last-15")
async def time_series_daily_last_15(symbol: str):
    """Return the most recent 15 days of daily data for a symbol.

    Parameters:
        symbol: Stock symbol.

    Returns:
        dict: Filtered daily series with metadata.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Returns fewer than 15 entries if data is sparse.
    """
    try:
        _validate_symbol(symbol)
        payload = await client.get_time_series_daily(symbol)
        series = _extract_daily_series(payload)
        return {
            "symbol": symbol.upper(),
            "days": 15,
            "data": _filter_last_days(series, 15),
        }
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/daily/{symbol}/last-30")
async def time_series_daily_last_30(symbol: str):
    """Return the most recent 30 days of daily data for a symbol.

    Parameters:
        symbol: Stock symbol.

    Returns:
        dict: Filtered daily series with metadata.

    Raises:
        HTTPException: For validation and upstream errors.

    Edge Cases:
        Returns fewer than 30 entries if data is sparse.
    """
    try:
        _validate_symbol(symbol)
        payload = await client.get_time_series_daily(symbol)
        series = _extract_daily_series(payload)
        return {
            "symbol": symbol.upper(),
            "days": 30,
            "data": _filter_last_days(series, 30),
        }
    except Exception as e:
        _handle_error(e)


@router.get("/cache/time-series/daily/{symbol}")
def cached_time_series_daily(
    symbol: str,
    include_stale: bool = Query(default=False),
):
    """Return cached daily series data from SQLite.

    Parameters:
        symbol: Stock symbol.
        include_stale: If True, return stale entries.

    Returns:
        dict: Cached payload with metadata.

    Raises:
        HTTPException: 404 if no cache entry exists.

    Edge Cases:
        Returns stale data only when include_stale is True.
    """
    try:
        _validate_symbol(symbol)
        cached = client.get_cached_time_series_daily(
            symbol,
            allow_stale=include_stale,
        )
        if not cached:
            raise HTTPException(status_code=404, detail="No cached data found.")
        return {
            "symbol": symbol.upper(),
            "data": cached["payload"],
            "cached_at": cached["fetched_at"],
            "ttl_seconds": cached["ttl_seconds"],
            "stale": cached["stale"],
        }
    except Exception as e:
        _handle_error(e)


@router.get("/cache/quote/{symbol}")
def cached_global_quote(
    symbol: str,
    include_stale: bool = Query(default=False),
):
    """Return cached global quote data from SQLite.

    Parameters:
        symbol: Stock symbol.
        include_stale: If True, return stale entries.

    Returns:
        dict: Cached payload with metadata.

    Raises:
        HTTPException: 404 if no cache entry exists.

    Edge Cases:
        Returns stale data only when include_stale is True.
    """
    try:
        _validate_symbol(symbol)
        cached = client.get_cached_global_quote(
            symbol,
            allow_stale=include_stale,
        )
        if not cached:
            raise HTTPException(status_code=404, detail="No cached data found.")
        return {
            "symbol": symbol.upper(),
            "data": cached["payload"],
            "cached_at": cached["fetched_at"],
            "ttl_seconds": cached["ttl_seconds"],
            "stale": cached["stale"],
        }
    except Exception as e:
        _handle_error(e)


@router.get("/cache/company-overview/{symbol}")
def cached_company_overview(
    symbol: str,
    include_stale: bool = Query(default=False),
):
    """Return cached company overview data from SQLite.

    Parameters:
        symbol: Stock symbol.
        include_stale: If True, return stale entries.

    Returns:
        dict: Cached payload with metadata.

    Raises:
        HTTPException: 404 if no cache entry exists.

    Edge Cases:
        Returns stale data only when include_stale is True.
    """
    try:
        _validate_symbol(symbol)
        cached = client.get_cached_company_overview(
            symbol,
            allow_stale=include_stale,
        )
        if not cached:
            raise HTTPException(status_code=404, detail="No cached data found.")
        return {
            "symbol": symbol.upper(),
            "data": cached["payload"],
            "cached_at": cached["fetched_at"],
            "ttl_seconds": cached["ttl_seconds"],
            "stale": cached["stale"],
        }
    except Exception as e:
        _handle_error(e)
