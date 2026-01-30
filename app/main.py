from fastapi import FastAPI
from app.routes.alphavantage import router as alphavantage_router

app = FastAPI()

app.include_router(alphavantage_router, prefix="/api")
