from fastapi import APIRouter, HTTPException
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
    if not symbol or len(symbol) > 10 or not symbol.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid symbol format.")


def _validate_keywords(keywords: str):
    if not keywords or len(keywords) > 50:
        raise HTTPException(status_code=400, detail="Invalid keywords.")


def _extract_daily_series(payload: dict) -> dict:
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise HTTPException(
            status_code=502,
            detail="Upstream daily series data missing.",
        )
    return series


def _filter_last_days(series: dict, days: int) -> dict:
    dates = sorted(series.keys(), reverse=True)
    recent_dates = dates[:days]
    return {date: series[date] for date in recent_dates}


def _handle_error(error: Exception):
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
    try:
        _validate_symbol(symbol)
        data = await client.get_global_quote(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/app/search-symbol/{keywords}")
async def search_symbol(keywords: str):
    try:
        _validate_keywords(keywords)
        data = await client.search_symbol(keywords)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/daily/{symbol}")
async def time_series_daily(symbol: str):
    try:
        _validate_symbol(symbol)
        data = await client.get_time_series_daily(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/weekly/{symbol}")
async def time_series_weekly(symbol: str):
    try:
        _validate_symbol(symbol)
        data = await client.get_time_series_weekly(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/monthly/{symbol}")
async def time_series_monthly(symbol: str):
    try:
        _validate_symbol(symbol)
        data = await client.get_time_series_monthly(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/gold-spot-price")
async def gold_spot_price():
    try:
        data = await client.get_gold_spot_price()
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/silver-spot-price")
async def silver_spot_price():
    try:
        data = await client.get_silver_spot_price()
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/company-overview/{symbol}")
async def company_overview(symbol: str):
    try:
        _validate_symbol(symbol)
        data = await client.get_company_overview(symbol)
        return data
    except Exception as e:
        _handle_error(e)


@router.get("/time-series/daily/{symbol}/last-7")
async def time_series_daily_last_7(symbol: str):
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
