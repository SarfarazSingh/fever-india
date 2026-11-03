import logging
import secrets
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import ASSET_DIR, BOARDING_PASS_DIR, STATIC_DIR, get_settings
from app.database import engine, init_db
from app.routers import bookings, demo, flights, profile, webhooks
from app.services.scheduler import rehydrate_jobs, scheduler
from app.services.duffel import close_duffel_client, DuffelError
from app.v1.routes import router as v1_router
from app.v1.integrations import router as integration_router
from app.v1.auth_google import router as google_auth_router

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("concierge")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

if settings.sentry_dsn:
    import sentry_sdk

    def redact_event(event, hint):
        request = event.get("request", {})
        request.pop("data", None)
        request.pop("cookies", None)
        request.pop("query_string", None)
        if isinstance(request.get("url"), str):
            request["url"] = request["url"].partition("?")[0]
        request["headers"] = {
            k: v
            for k, v in request.get("headers", {}).items()
            if k.lower() not in {"cookie", "authorization", "x-csrf-token"}
        }
        event.pop("user", None)
        return event

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        send_default_pii=False,
        before_send=redact_event,
        traces_sample_rate=0.1,
    )

BOARDING_PASS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.production:
        if (
            not settings.database_url.startswith("postgresql")
            or not settings.email_allowlist
        ):
            raise RuntimeError("Production requires PostgreSQL and ALLOWED_EMAILS")
        if (
            settings.legacy_api_enabled
            or settings.auto_checkin_enabled
            or settings.demo_enabled
        ):
            raise RuntimeError(
                "Production requires legacy API, demo access, and automated check-in to be disabled"
            )
        if (
            not settings.supabase_url
            or not settings.supabase_anon_key
            or not settings.app_url.startswith("https://")
        ):
            raise RuntimeError("Production requires Supabase Auth and an HTTPS APP_URL")
        if not settings.login_methods:
            raise RuntimeError("Production requires a configured sign-in method")
        if settings.auth_google_enabled:
            from cryptography.fernet import Fernet

            Fernet(settings.token_encryption_key.encode())
    await init_db()
    if settings.production:
        from app.v1.jobs import queue

        await queue.open_async()
    if settings.auto_checkin_enabled and not settings.production:
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
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await close_duffel_client()
        if settings.production:
            await queue.close_async()
        await engine.dispose()


app = FastAPI(
    title="Business Class Flight Concierge",
    version="2.0.0",
    description="Private travel concierge with explainable flight search, complete itineraries and staged card checkout.",
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
app.add_middleware(GZipMiddleware, minimum_size=1000)

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
if (WEB_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="web-assets")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path.startswith(
        "/api/v1/"
    ):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != settings.app_url.rstrip("/"):
            return JSONResponse(
                {"detail": "Request origin is not allowed"}, status_code=403
            )
        if int(request.headers.get("content-length", "0")) > 1_000_000:
            return JSONResponse(
                {"detail": "Request body is too large"}, status_code=413
            )
    # No old, unauthenticated mutation path can bypass the v1 state machine.
    if request.url.path == "/api/bookings/place":
        return JSONResponse(
            {"detail": "Use the authenticated checkout flow"}, status_code=410
        )
    if request.url.path.startswith("/static/boarding_passes"):
        return JSONResponse(
            {"detail": "Use authenticated trip documents"}, status_code=404
        )
    if (
        settings.legacy_api_enabled
        and request.url.path.startswith("/api/")
        and not request.url.path.startswith("/api/v1/")
    ):
        from app.v1.security import current_account
        from app.database import SessionLocal

        try:
            async with SessionLocal() as db:
                await current_account(request, db)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if settings.production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' https://js.evervault.com; connect-src 'self' https://*.duffel.com https://*.sentry.io https://*.evervault.com; frame-src https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
    return response


@app.exception_handler(DuffelError)
async def provider_error(request: Request, exc: DuffelError):
    return JSONResponse(
        {
            "detail": "The airline provider could not complete this request. Please try again shortly."
        },
        status_code=502,
    )


@app.get("/", include_in_schema=False)
async def web_app():
    if (WEB_DIST / "index.html").exists():
        return FileResponse(WEB_DIST / "index.html")
    return RedirectResponse(settings.app_url, status_code=307)


@app.get("/airports.json", include_in_schema=False)
async def airport_list() -> FileResponse:
    return FileResponse(ASSET_DIR / "airports.json", media_type="application/json")


app.include_router(v1_router)
app.include_router(integration_router)
app.include_router(google_auth_router)
if settings.legacy_api_enabled and settings.environment == "test":
    app.include_router(flights.router)
    app.include_router(profile.router)
    app.include_router(bookings.router)
    app.include_router(webhooks.router)
    app.include_router(demo.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
    }


@app.get("/{path:path}", include_in_schema=False)
async def spa(path: str):
    if path.startswith(("api/", "static/")):
        raise HTTPException(404, "Not found")
    candidate = (WEB_DIST / path).resolve()
    if WEB_DIST.resolve() in candidate.parents and candidate.is_file():
        return FileResponse(candidate)
    if (WEB_DIST / "index.html").exists():
        return FileResponse(WEB_DIST / "index.html")
    raise HTTPException(404, "Start the web development server or build web/dist")
