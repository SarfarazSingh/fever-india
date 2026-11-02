import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import BOARDING_PASS_DIR, STATIC_DIR, get_settings
from app.database import engine, init_db
from app.routers import bookings, demo, flights, webhooks
from app.services.scheduler import rehydrate_jobs, scheduler

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("concierge")

BOARDING_PASS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.start()
    await rehydrate_jobs()
    logger.info(
        "Concierge API ready (flyo=%s, provider=%s, lead=%sh)",
        "on" if settings.flyo_enabled else "off",
        settings.flight_provider,
        settings.checkin_lead_hours,
    )
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await engine.dispose()


app = FastAPI(
    title="Business Class Flight Concierge",
    version="1.0.0",
    description="Business Class search with airline deep links and automated 24-hour check-in.",
    lifespan=lifespan,
)

origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(flights.router)
app.include_router(bookings.router)
app.include_router(webhooks.router)
app.include_router(demo.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
        "scheduler_running": scheduler.running,
        "scheduled_jobs": len(scheduler.get_jobs()) if scheduler.running else 0,
    }
