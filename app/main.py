from contextlib import asynccontextmanager
import aiosqlite

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .api.chat import router as chat_router
from .agent.state import build_graph

# TODO: Where to load env variables?


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = await aiosqlite.connect("checkpoints.db")
    app.state.saver = AsyncSqliteSaver(conn)
    app.state.graph = build_graph(app.state.saver)

    yield

    await conn.close()


app = FastAPI(
    title="Jarvis API",
    description="Backend API for Jarvis",
    version="1.0.0",
    lifespan=lifespan,
)

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
