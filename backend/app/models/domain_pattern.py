from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, JSON, String
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class DomainPattern(SQLModel, table=True):
    __tablename__ = "domain_patterns"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    domain: str = Field(
        sa_column=Column(String(length=255), nullable=False, unique=True),
    )
    is_catch_all: bool | None = Field(default=None)
    patterns: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    last_successful_pattern: str | None = Field(default=None, max_length=128)
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
