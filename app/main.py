import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.routers import glucose, health, insulin

logging.basicConfig(level=settings.LOG_LEVEL)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.poller.dexcom import poll_dexcom

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        poll_dexcom,
        trigger="interval",
        minutes=settings.POLL_INTERVAL_MINUTES,
        id="dexcom_poller",
        replace_existing=True,
        next_run_time=datetime.now(UTC),
    )

    if settings.tandem_enabled:
        from app.poller.tandem import poll_tandem

        scheduler.add_job(
            poll_tandem,
            trigger="interval",
            minutes=settings.TANDEM_POLL_INTERVAL_MINUTES,
            id="tandem_poller",
            replace_existing=True,
            next_run_time=datetime.now(UTC),
        )
    else:
        logging.getLogger(__name__).info(
            "Tandem credentials not configured — skipping Tandem poller"
        )

    scheduler.start()
    app.state.scheduler = scheduler
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="OS-Me Health API",
    description="Public read-only API for personal health data. "
    "Glucose data is polled from Dexcom Share every 5 minutes.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_credentials=False,
)

app.include_router(health.router)
app.include_router(glucose.router)
app.include_router(insulin.basal_router)
app.include_router(insulin.bolus_router)
