from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.queue import close_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    if not hasattr(app.state, "redis_pool"):
        app.state.redis_pool = None
    yield
    await close_redis_pool(app)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)
app.include_router(api_router)
