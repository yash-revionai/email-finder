from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import field_validator
from sqlmodel import SQLModel, Session

from app.core.database import get_session
from app.core.queue import get_redis_pool
from app.models.base import utcnow
from app.models.lookup import Lookup

router = APIRouter(prefix="/api/lookup", tags=["lookup"])


class LookupCreateRequest(SQLModel):
    first_name: str
    last_name: str
    domain: str

    @field_validator("first_name", "last_name", "domain", mode="before")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be empty")
        return normalized


class LookupQueuedResponse(SQLModel):
    id: UUID
    status: str


class LookupRead(SQLModel):
    id: UUID
    first_name: str
    last_name: str
    domain: str
    email: str | None
    confidence: float
    reason_code: str
    verifier_calls_used: int
    status: str
    created_at: datetime
    completed_at: datetime | None


@router.post("", response_model=LookupQueuedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_lookup(
    payload: LookupCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> LookupQueuedResponse:
    lookup = Lookup(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        domain=_normalize_domain(payload.domain),
        status="pending",
    )
    session.add(lookup)
    session.commit()
    session.refresh(lookup)

    try:
        redis_pool = await get_redis_pool(request)
        await redis_pool.enqueue_job("run_lookup", str(lookup.id))
    except Exception as exc:
        lookup.status = "failed"
        lookup.completed_at = utcnow()
        session.add(lookup)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lookup queue is unavailable",
        ) from exc

    return LookupQueuedResponse(id=lookup.id, status=lookup.status)


@router.get("/{lookup_id}", response_model=LookupRead)
def get_lookup(lookup_id: UUID, session: Session = Depends(get_session)) -> LookupRead:
    lookup = session.get(Lookup, lookup_id)
    if lookup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lookup not found")

    return _serialize_lookup(lookup)


def _serialize_lookup(lookup: Lookup) -> LookupRead:
    return LookupRead(
        id=lookup.id,
        first_name=lookup.first_name,
        last_name=lookup.last_name,
        domain=lookup.domain,
        email=lookup.email,
        confidence=lookup.confidence,
        reason_code=lookup.reason_code,
        verifier_calls_used=lookup.verifier_calls_used,
        status=lookup.status,
        created_at=lookup.created_at,
        completed_at=lookup.completed_at,
    )


def _normalize_domain(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.removeprefix("https://").removeprefix("http://")
    normalized = normalized.split("/", maxsplit=1)[0]
    return normalized.lstrip("@")
