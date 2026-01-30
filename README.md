# Financial-Analysis

A backend financial analysis tool built as a structured, milestone-based learning project. The app starts with a minimal FastAPI service and grows toward a fully featured API that fetches, stores, and analyzes market data.

## Why

This project is designed to practice real backend workflows: building APIs, integrating external data sources, and evolving a codebase over time. It provides a practical path from "hello world" to a usable financial analysis backend.

## What

The service now exposes multiple market-data endpoints backed by Alpha Vantage. It supports async fetches, structured error handling, logging for all external API calls, and a 2-minute in-memory cache to reduce rate-limit pressure.

## How

- **Framework:** FastAPI
- **Workflow:** Milestones that expand the API, storage, and analysis capabilities
- **Quality:** Linting via flake8 and CI checks in GitHub Actions
- **External API:** Alpha Vantage (configured via environment variables)

## Project Roadmap

1. **Milestone 1 - Project Setup**
   - FastAPI app and basic endpoint
   - README, linting, CI, and Git setup
2. **Milestone 2 - External Data**
   - Fetch data from a public financial API
   - Add endpoints and error handling
3. **Milestone 3 - Persistence**
   - Store data locally (file or SQLite)
   - Avoid redundant fetches
4. **Milestone 4 - Data Mutation**
   - Add models and CRUD endpoints
   - Validation for all inputs
5. **Milestone 5 - Analysis**
   - Aggregations (averages, highs/lows, trends)
   - Optional auth and background refresh
6. **Milestone 6 - Dashboards and Docs**
   - Dashboard endpoints
   - OpenAPI docs and final demo

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs` for the interactive API docs.

## Environment

Create a `.env` file in the project root:

```bash
ALPHAVANTAGE_API_KEY=your_key_here
ALPHAVANTAGE_BASE_URL=https://www.alphavantage.co/query
```

## API Endpoints (prefix: /api)

- `GET /stock-price/{symbol}`
- `GET /time-series/daily/{symbol}`
- `GET /time-series/daily/{symbol}/last-7`
- `GET /time-series/daily/{symbol}/last-15`
- `GET /time-series/daily/{symbol}/last-30`
- `GET /time-series/weekly/{symbol}`
- `GET /time-series/monthly/{symbol}`
- `GET /company-overview/{symbol}`
- `GET /gold-spot-price`
- `GET /silver-spot-price`
- `GET /app/search-symbol/{keywords}`

## Error Handling

- **400**: Invalid request format (e.g., symbol/keywords validation)
- **401**: Authentication failure
- **404**: Invalid symbol
- **429**: Rate limit exceeded
- **503**: Upstream service issues
- **500**: Unexpected errors

## Caching

All external API responses are cached in memory for 2 minutes to reduce repeated calls and avoid rate limits.

## Logging

All external API requests are logged (start, success, and failure cases) in the Alpha Vantage service layer.

## Tests

```bash
pytest
```
