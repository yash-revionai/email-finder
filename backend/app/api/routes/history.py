from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import SQLModel, Session, select

from app.core.database import get_session
from app.models.lookup import Lookup

router = APIRouter(prefix="/api/history", tags=["history"])


class HistoryItem(SQLModel):
    id: UUID
    first_name: str
    last_name: str
    domain: str
    email: str | None
    confidence: float
    reason_code: str
    status: str
    created_at: datetime
    completed_at: datetime | None


class HistoryResponse(SQLModel):
    page: int
    limit: int
    total: int
    items: list[HistoryItem]


@router.get("", response_model=HistoryResponse)
def get_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    domain: str | None = Query(default=None),
    status: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> HistoryResponse:
    total_query = _apply_history_filters(select(func.count()).select_from(Lookup), domain, status)
    history_query = _apply_history_filters(select(Lookup), domain, status)
    history_query = history_query.order_by(Lookup.created_at.desc()).offset((page - 1) * limit).limit(limit)

    total = int(session.exec(total_query).one())
    items = session.exec(history_query).all()

    return HistoryResponse(
        page=page,
        limit=limit,
        total=total,
        items=[
            HistoryItem(
                id=item.id,
                first_name=item.first_name,
                last_name=item.last_name,
                domain=item.domain,
                email=item.email,
                confidence=item.confidence,
                reason_code=item.reason_code,
                status=item.status,
                created_at=item.created_at,
                completed_at=item.completed_at,
            )
            for item in items
        ],
    )


def _apply_history_filters(query, domain: str | None, status: str | None):
    if domain:
        query = query.where(Lookup.domain.ilike(f"%{domain.strip().lower()}%"))
    if status:
        query = query.where(Lookup.status == status.strip().lower())
    return query
