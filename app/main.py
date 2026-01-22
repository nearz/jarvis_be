from contextlib import asynccontextmanager
import aiosqlite

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .api.models import router as models_router
from .api.projects import router as project_router
from .api.chat import router as chat_router
from .api.auth import router as auth_router
from .api.history import router as history_router
from .agent.state import build_graph
from .agent.tavily_client import get_async_tavily_client, MissingApiKey
from .core.config import settings
from .core.logging import setup_logging, get_logger
from .core.db_ops.app_db import init_app_db, AppDatabase
from .middleware import LoggingMiddleware, DelayMiddleware

from dotenv import load_dotenv

load_dotenv()

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        checkpoints_conn = await aiosqlite.connect("checkpoints.db")
        app.state.saver = AsyncSqliteSaver(checkpoints_conn)
        app.state.graph = build_graph(app.state.saver)

        app_db_conn = await aiosqlite.connect("app.db")
        await init_app_db(app_db_conn)
        app.state.app_db = AppDatabase(app_db_conn)

        try:
            get_async_tavily_client()
        except MissingApiKey:
            logger.exception("Tavily API key not set.")
            raise RuntimeError("Tavily API key not set.")

    except Exception as e:
        logger.exception("Failed to initialize application: %s", e)
        raise

    logger.info("Application Started | Version %s", app.version)
    yield

    await checkpoints_conn.close()
    await app_db_conn.close()
    get_async_tavily_client.cache_clear()
    logger.info("Application Stopped")


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VER,
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(DelayMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models_router)
app.include_router(project_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(history_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Jarvis API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# if __name__ == "__main__":
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True
#     )
