import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

os.makedirs("data", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = create_scheduler()
    scheduler.start()
    logging.getLogger(__name__).info("Scheduler started. Morning check at %s:00 (%s)",
                                     app.state.check_hour if hasattr(app.state, "check_hour") else "07",
                                     "Europe/Vienna")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Instagram Creator Tracker",
    description="Persönlicher Tracker für Instagram Creator",
    version="1.0.0",
    lifespan=lifespan,
)

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

from app.routers import creators, jobs  # noqa: E402

app.include_router(creators.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}
