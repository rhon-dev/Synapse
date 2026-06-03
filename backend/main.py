"""Synapse FastAPI entrypoint."""
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Load .env before importing routes (so they see env vars at import time)
load_dotenv(Path(__file__).parent / ".env")

from backend.db.mongo import close_mongo_connection, connect_to_mongo  # noqa: E402
from backend.routes import atlas as atlas_routes  # noqa: E402
from backend.routes import chat as chat_routes  # noqa: E402
from backend.routes import sessions as session_routes  # noqa: E402
from backend.services.atlas import close_atlas_client  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup is best-effort: under serverless (Vercel), a raised exception
    # here aborts the whole app with "Application startup failed. Exiting."
    # — which 500s every endpoint, even /healthz. Mongo connection is now
    # lazy (see backend/db/mongo.py), so this is just a defensive guard
    # against any future startup side-effect.
    try:
        await connect_to_mongo()
    except Exception as exc:
        print(f"[lifespan startup] connect_to_mongo failed (non-fatal): {exc}")
    try:
        yield
    finally:
        try:
            await close_mongo_connection()
        except Exception as exc:
            print(f"[lifespan shutdown] close_mongo_connection failed: {exc}")
        try:
            await close_atlas_client()
        except Exception as exc:
            print(f"[lifespan shutdown] close_atlas_client failed: {exc}")


app = FastAPI(
    title="Synapse",
    description="Virtual AI Study Partner — chat + dynamic quizzes.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(chat_routes.router, tags=["chat"])
app.include_router(session_routes.router, tags=["sessions"])
app.include_router(atlas_routes.router)


@app.get("/healthz", tags=["health"])
async def healthz() -> dict:
    return {"status": "ok"}


# Static frontend ---------------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")
