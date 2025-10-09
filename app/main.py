import uuid
from contextlib import asynccontextmanager
import logging
import aiosqlite

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .api.chat import router as chat_router
from .agent.state import build_graph
from .agent.tavily_client import get_async_tavily_client, MissingApiKey
from .core.config import settings
from .core.logging import setup_logging, get_logger
from .middleware import LoggingMiddleware

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


# TODO: Test the exceptions in mocks
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        conn = await aiosqlite.connect("checkpoints.db")
        app.state.saver = AsyncSqliteSaver(conn)
        app.state.graph = build_graph(app.state.saver)
        try:
            get_async_tavily_client()
        except MissingApiKey:
            logger.exception("Tavily API key not set.")
            raise RuntimeError("Tavily API key not set.")

    except Exception as e:
        logger.exception(f"Failed to initialize application: %s", e)
        raise

    logger.info("Application Started | Version %s", app.version)
    yield

    await conn.close()
    get_async_tavily_client.cache_clear()
    logger.info("Application Stopped")


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VER,
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


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
