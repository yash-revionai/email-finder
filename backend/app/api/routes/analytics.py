from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlmodel import SQLModel, Session, select

from app.core.database import get_session
from app.models.lookup import Lookup
from app.models.verifier_call import VerifierCall

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

SUCCESS_REASON_CODES = {"valid", "exa_found", "scraped", "pattern_derived", "catch_all"}


class AnalyticsSummary(SQLModel):
    total_lookups: int
    overall_hit_rate: float
    credits_used_this_month: int


class WeeklyVolumePoint(SQLModel):
    week_start: datetime
    lookups: int


class DomainHitRatePoint(SQLModel):
    domain: str
    total_lookups: int
    hits: int
    hit_rate: float


class WeeklyCreditsPoint(SQLModel):
    week_start: datetime
    credits_used: int


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(session: Session = Depends(get_session)) -> AnalyticsSummary:
    total_lookups = int(session.exec(select(func.count()).select_from(Lookup)).one())
    hit_count = int(
        session.exec(
            select(func.count()).select_from(Lookup).where(Lookup.reason_code.in_(SUCCESS_REASON_CODES))
        ).one()
    )
    month_start = _month_start(datetime.now(timezone.utc))
    credits_used_this_month = session.exec(
        select(func.coalesce(func.sum(VerifierCall.credits_used), 0)).where(VerifierCall.called_at >= month_start)
    ).one()

    hit_rate = 0.0
    if total_lookups:
        hit_rate = round(hit_count / total_lookups, 4)

    return AnalyticsSummary(
        total_lookups=total_lookups,
        overall_hit_rate=hit_rate,
        credits_used_this_month=int(credits_used_this_month or 0),
    )


@router.get("/volume", response_model=list[WeeklyVolumePoint])
def get_volume(session: Session = Depends(get_session)) -> list[WeeklyVolumePoint]:
    week_points = _weekly_points(
        session,
        model_column=Lookup.created_at,
        aggregate_column=func.count(Lookup.id),
    )
    return [
        WeeklyVolumePoint(week_start=week_start, lookups=value)
        for week_start, value in week_points
    ]


@router.get("/domains", response_model=list[DomainHitRatePoint])
def get_top_domains(session: Session = Depends(get_session)) -> list[DomainHitRatePoint]:
    hit_case = case((Lookup.reason_code.in_(SUCCESS_REASON_CODES), 1), else_=0)
    rows = session.exec(
        select(
            Lookup.domain,
            func.count(Lookup.id),
            func.sum(hit_case),
        ).group_by(Lookup.domain)
    ).all()

    points: list[DomainHitRatePoint] = []
    for domain, total, hits in rows:
        total_lookups = int(total or 0)
        hit_count = int(hits or 0)
        if total_lookups == 0:
            continue

        points.append(
            DomainHitRatePoint(
                domain=domain,
                total_lookups=total_lookups,
                hits=hit_count,
                hit_rate=round(hit_count / total_lookups, 4),
            )
        )

    return sorted(points, key=lambda point: (-point.hit_rate, -point.hits, -point.total_lookups, point.domain))[:10]


@router.get("/credits", response_model=list[WeeklyCreditsPoint])
def get_weekly_credits(session: Session = Depends(get_session)) -> list[WeeklyCreditsPoint]:
    week_points = _weekly_points(
        session,
        model_column=VerifierCall.called_at,
        aggregate_column=func.coalesce(func.sum(VerifierCall.credits_used), 0),
        source_model=VerifierCall,
    )
    return [
        WeeklyCreditsPoint(week_start=week_start, credits_used=value)
        for week_start, value in week_points
    ]


def _weekly_points(session: Session, *, model_column, aggregate_column, source_model=Lookup) -> list[tuple[datetime, int]]:
    first_week = _week_start(datetime.now(timezone.utc) - timedelta(weeks=11))
    week_bucket = func.date_trunc("week", model_column)
    rows = session.exec(
        select(week_bucket, aggregate_column)
        .select_from(source_model)
        .where(model_column >= first_week)
        .group_by(week_bucket)
        .order_by(week_bucket)
    ).all()

    values_by_week = {
        _ensure_utc(week_start): int(value or 0)
        for week_start, value in rows
    }
    ordered_points: list[tuple[datetime, int]] = []

    for offset in range(12):
        week_start = first_week + timedelta(weeks=offset)
        ordered_points.append((week_start, values_by_week.get(week_start, 0)))

    return ordered_points


def _month_start(value: datetime) -> datetime:
    utc_value = _ensure_utc(value)
    return utc_value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _week_start(value: datetime) -> datetime:
    utc_value = _ensure_utc(value)
    start = utc_value - timedelta(days=utc_value.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
