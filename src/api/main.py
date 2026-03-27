"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from contextlib import asynccontextmanager
import logging

# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.cron import CronTrigger

from .routers import pdfs, query, models, health
from .database import engine, Base
from .config import settings
# from src.jobs.daily_status_report import run_daily_report

# Create database tables
Base.metadata.create_all(bind=engine)

# scheduler = AsyncIOScheduler()


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Schedule daily report at 8:00 AM every day
#     scheduler.add_job(
#         run_daily_report,
#         trigger=CronTrigger(hour=8, minute=0),
#         id="daily_status_report",
#         replace_existing=True,
#     )
#     scheduler.start()
#     print("[Scheduler] Daily status report job scheduled at 8:00 AM.")
#     yield
#     scheduler.shutdown()


# Initialize FastAPI
app = FastAPI(
    title="Ollama PDF RAG API",
    description="REST API for PDF-based RAG with Ollama",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pdfs.router)
app.include_router(query.router)
app.include_router(models.router)
app.include_router(health.router)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Ollama PDF RAG API",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
