from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class Lookup(SQLModel, table=True):
    __tablename__ = "lookups"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    first_name: str = Field(index=True, max_length=255)
    last_name: str = Field(index=True, max_length=255)
    domain: str = Field(index=True, max_length=255)
    email: str | None = Field(default=None, index=True, max_length=320)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_code: str = Field(default="not_found", max_length=64)
    verifier_calls_used: int = Field(default=0, ge=0, le=3)
    status: str = Field(default="pending", index=True, max_length=32)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
