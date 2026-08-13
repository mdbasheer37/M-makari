import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import os

from database import engine, Base, check_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("makari")

IS_PRODUCTION = os.getenv("ENVIRONMENT", "production") == "production"

from routers import (
    auth, lectures, videos, audio, categories,
    search, favorites, downloads, notifications,
    library, live, admin, users, prayer
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Test DB connection — log only, never crash the process for a
    #    temporary outage. The /health endpoint reports real status.
    db_ok = check_db_connection()

    # 2. Create all tables (safe — only creates what doesn't exist).
    #    Guarded: a DB hiccup at boot should not crash the whole app.
    if db_ok:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables ready")
        except Exception as e:
            logger.error(f"Table creation failed: {e}")

        # 3. Seed initial data (safe — skips existing records)
        try:
            from seed import seed
            seed()
        except Exception as e:
            logger.warning(f"Seed skipped: {e}")
    else:
        logger.error("Skipping table creation/seed — database unavailable at startup")

    yield
    logger.info("Shutting down Makari Islamic TV API")


app = FastAPI(
    title="Makari Islamic TV API",
    description="Complete Islamic streaming platform for Malam Ibrahim Makari",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — environment-based. The API is consumed with a Bearer JWT in the
# Authorization header (not cookies), so credentials are not required and
# we do not enable allow_credentials — that keeps a wildcard origin safe.
# Set ALLOWED_ORIGINS (comma-separated) in production to restrict to your
# real frontend domain(s), e.g. "https://makari.tv,https://www.makari.tv".
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if _allowed_origins_env:
    ALLOWED_ORIGINS = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = ["*"]
    if IS_PRODUCTION:
        logger.warning(
            "ALLOWED_ORIGINS not set — CORS is wide open (*). "
            "Set ALLOWED_ORIGINS in production to your frontend domain(s)."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handling — never leak tracebacks/SQL/secrets to clients ──
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request data", "errors": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error. Please try again later."})


# Media file serving
for folder in ["media/videos", "media/audio", "media/images", "media/pdfs", "media/thumbnails"]:
    os.makedirs(folder, exist_ok=True)

app.mount("/media", StaticFiles(directory="media"), name="media")

# ── Routers ──────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api/auth",          tags=["Authentication"])
app.include_router(users.router,         prefix="/api/users",         tags=["Users"])
app.include_router(lectures.router,      prefix="/api/lectures",      tags=["Lectures"])
app.include_router(videos.router,        prefix="/api/videos",        tags=["Videos"])
app.include_router(audio.router,         prefix="/api/audio",         tags=["Audio"])
app.include_router(categories.router,    prefix="/api/categories",    tags=["Categories"])
app.include_router(search.router,        prefix="/api/search",        tags=["Search"])
app.include_router(favorites.router,     prefix="/api/favorites",     tags=["Favorites"])
app.include_router(downloads.router,     prefix="/api/downloads",     tags=["Downloads"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(library.router,       prefix="/api/library",       tags=["Library"])
app.include_router(live.router,          prefix="/api/live",          tags=["Live Streaming"])
app.include_router(admin.router,         prefix="/api/admin",         tags=["Admin"])
app.include_router(prayer.router,        prefix="/api/prayer",        tags=["Prayer Times"])


@app.get("/", tags=["Status"])
async def root():
    return {
        "app": "Makari Islamic TV",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Status"])
async def health():
    from database import check_db_connection
    db_ok = check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
    }
