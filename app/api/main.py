import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

from agents import set_default_openai_api, set_tracing_disabled

set_tracing_disabled(True)
set_default_openai_api('chat_completions')

from app.core.config import get_settings
from app.db.models import init_db
from app.db.seed import seed_database
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.api.ws import router as ws_router
from app.cache.redis_client import close_redis
from app.ml.model_inference import load_model
from app.ml.shap_explainer import load_explainer

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_database()
    load_model()
    load_explainer()
    yield
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    description="Real-time multi-agent fraud detection with COD fraud focus",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(ws_router, prefix="/api")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
