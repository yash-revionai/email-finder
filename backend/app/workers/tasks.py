from __future__ import annotations

from typing import Any
from uuid import UUID

from arq.connections import RedisSettings
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine
from app.models.base import utcnow
from app.models.lookup import Lookup
from app.services.email_finder import run_email_finder as run_email_finder_service

SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


async def startup(ctx: dict[str, Any]) -> None:
    ctx["session_factory"] = SessionFactory


async def shutdown(ctx: dict[str, Any]) -> None:
    ctx.pop("session_factory", None)
    engine.dispose()


async def run_lookup(ctx: dict[str, Any], lookup_id: str | UUID) -> dict[str, str]:
    session_factory = ctx.get("session_factory", SessionFactory)
    lookup_uuid = lookup_id if isinstance(lookup_id, UUID) else UUID(str(lookup_id))

    with session_factory() as session:
        try:
            lookup = await run_email_finder_service(lookup_uuid, session)
            return {"id": str(lookup.id), "status": lookup.status}
        except Exception:
            session.rollback()
            lookup = session.get(Lookup, lookup_uuid)
            if lookup is not None:
                lookup.status = "failed"
                lookup.completed_at = utcnow()
                session.add(lookup)
                session.commit()
            raise


class WorkerSettings:
    functions = [run_lookup]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
