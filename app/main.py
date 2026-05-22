from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import lots

app = FastAPI(title="OpenPark - Hub Server")

if settings.frontend_url:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(lots.router, prefix="/api/v1", tags=["lots"])
