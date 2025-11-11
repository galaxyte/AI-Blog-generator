"""
FastAPI entry point for the AI Blog Generator application.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from .models.blog_model import Base
from .routes.blog_routes import router as blog_router
from .services.ai_service import AIService


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./blogs.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        ai_service = AIService()
        ai_error = None
    except RuntimeError as exc:
        ai_service = None
        ai_error = str(exc)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.db_engine = engine
    app.state.async_session = session_factory
    app.state.ai_service = ai_service
    app.state.ai_error = ai_error

    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title="AI Blog Generator",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(blog_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


