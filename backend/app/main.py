from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis import router as analysis_router
from app.api.analytics import router as analytics_router
from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.core.config import get_settings
from app.database.database import init_db
from app.utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    current = get_settings()
    current.video_dir.mkdir(parents=True, exist_ok=True)
    current.processed_path.mkdir(parents=True, exist_ok=True)
    current.results_path.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("%s backend starting (env=%s)", current.app_name, current.app_env)
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered wildlife detection, tracking, behaviour, and farm "
        "encounter-risk assessment from uploaded camera-trap videos."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
    }
