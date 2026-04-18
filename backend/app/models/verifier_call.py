from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class VerifierCall(SQLModel, table=True):
    __tablename__ = "verifier_calls"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lookup_id: UUID = Field(foreign_key="lookups.id", index=True)
    email: str = Field(index=True, max_length=320)
    verifier: str = Field(index=True, max_length=64)
    result: str = Field(index=True, max_length=32)
    credits_used: int = Field(default=1, ge=0)
    called_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
