# Financial-Analysis

A backend financial analysis tool built as a structured, milestone-based learning project. The app starts with a minimal FastAPI service and grows toward a fully featured API that fetches, stores, and analyzes market data.

## Why

This project is designed to practice real backend workflows: building APIs, integrating external data sources, and evolving a codebase over time. It provides a practical path from "hello world" to a usable financial analysis backend.

## What

Today, the service exposes a simple root endpoint that returns a hello world message. The planned direction is to fetch financial data from a public API, persist it, and expose analytics endpoints.

## How

- **Framework:** FastAPI
- **Workflow:** Milestones that expand the API, storage, and analysis capabilities
- **Quality:** Linting via flake8 and CI checks in GitHub Actions

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

Then visit `http://127.0.0.1:8000/`.
