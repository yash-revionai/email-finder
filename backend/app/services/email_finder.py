from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base import utcnow
from app.models.domain_pattern import DomainPattern
from app.models.lookup import Lookup
from app.models.verifier_call import VerifierCall
from app.services.catch_all_probe import is_catch_all
from app.services.exa_searcher import search_email
from app.services.firecrawl_scraper import scrape_domain_patterns
from app.services.pattern_engine import PATTERNS, generate_candidates, global_weight
from app.services.verifiers.omniverifier import OmniVerifier

EXA_BASE_CONFIDENCE = 0.85
FIRECRAWL_BASE_CONFIDENCE = 0.80
CATCH_ALL_CONFIDENCE = 0.50
MAX_VERIFIER_CALLS = 3
SOURCE_PRIORITY = {
    "exa_found": 0,
    "scraped": 1,
    "pattern_derived": 2,
}


@dataclass(slots=True)
class RankedCandidate:
    email: str
    confidence: float
    reason_code: str
    source_priority: int
    pattern: str | None = None


async def run_email_finder(lookup_id: UUID | str, db: Session) -> Lookup:
    lookup_uuid = lookup_id if isinstance(lookup_id, UUID) else UUID(str(lookup_id))
    lookup = db.get(Lookup, lookup_uuid)
    if lookup is None:
        raise ValueError(f"Lookup {lookup_uuid} does not exist")

    lookup.status = "processing"
    lookup.domain = _normalize_domain(lookup.domain)
    db.add(lookup)
    db.commit()
    db.refresh(lookup)

    domain_pattern = _get_or_create_domain_pattern(db, lookup.domain)

    catch_all = await asyncio.to_thread(is_catch_all, lookup.domain)
    domain_pattern = _get_or_create_domain_pattern(db, lookup.domain)
    if catch_all:
        lookup.email = None
        lookup.confidence = CATCH_ALL_CONFIDENCE
        lookup.reason_code = "catch_all"
        lookup.status = "done"
        lookup.completed_at = utcnow()
        domain_pattern.is_catch_all = True
        domain_pattern.updated_at = utcnow()
        db.add(domain_pattern)
        db.add(lookup)
        db.commit()
        db.refresh(lookup)
        return lookup

    exa_hits = await _safe_candidate_call(search_email, lookup.first_name, lookup.last_name, lookup.domain)
    firecrawl_hits = await _safe_candidate_call(scrape_domain_patterns, lookup.domain)
    pattern_hits = generate_candidates(lookup.first_name, lookup.last_name, lookup.domain, domain_pattern)

    candidates = rank_candidates(
        lookup.first_name,
        lookup.last_name,
        lookup.domain,
        exa_hits,
        firecrawl_hits,
        pattern_hits,
    )
    verifier = OmniVerifier()

    for index, candidate in enumerate(candidates[:MAX_VERIFIER_CALLS], start=1):
        verifier_result = await verifier.verify(candidate.email)
        lookup.verifier_calls_used = index
        _record_verifier_call(
            db,
            lookup_id=lookup.id,
            email=candidate.email,
            verifier_name=verifier.name,
            result=verifier_result.result,
            credits_used=verifier_result.credits_used,
        )

        if candidate.pattern:
            _update_pattern_stats(
                domain_pattern,
                candidate.pattern,
                success=verifier_result.result == "valid",
            )
            db.add(domain_pattern)

        if verifier_result.result == "valid":
            lookup.email = candidate.email
            lookup.confidence = _verified_confidence(candidate.confidence)
            lookup.reason_code = candidate.reason_code
            lookup.status = "done"
            lookup.completed_at = utcnow()
            db.add(lookup)
            db.commit()
            db.refresh(lookup)
            return lookup

        if verifier_result.result == "catch_all":
            lookup.email = candidate.email
            lookup.confidence = CATCH_ALL_CONFIDENCE
            lookup.reason_code = "catch_all"
            lookup.status = "done"
            lookup.completed_at = utcnow()
            domain_pattern.is_catch_all = True
            domain_pattern.updated_at = utcnow()
            db.add(domain_pattern)
            db.add(lookup)
            db.commit()
            db.refresh(lookup)
            return lookup

    lookup.email = None
    lookup.confidence = 0.0
    lookup.reason_code = "not_found"
    lookup.status = "done"
    lookup.completed_at = utcnow()
    db.add(lookup)
    db.commit()
    db.refresh(lookup)
    return lookup


def rank_candidates(
    first_name: str,
    last_name: str,
    domain: str,
    exa_hits: list[str],
    firecrawl_hits: list[str],
    pattern_hits: list[tuple[str, float]],
) -> list[RankedCandidate]:
    ranked: dict[str, RankedCandidate] = {}

    def merge_candidate(candidate: RankedCandidate) -> None:
        existing = ranked.get(candidate.email)
        if existing is None:
            ranked[candidate.email] = candidate
            return

        if candidate.confidence > existing.confidence:
            ranked[candidate.email] = candidate
            return

        if candidate.confidence == existing.confidence and candidate.source_priority < existing.source_priority:
            ranked[candidate.email] = candidate

    for email in exa_hits:
        merge_candidate(
            RankedCandidate(
                email=email.lower(),
                confidence=EXA_BASE_CONFIDENCE,
                reason_code="exa_found",
                source_priority=SOURCE_PRIORITY["exa_found"],
                pattern=infer_pattern(first_name, last_name, email, domain),
            )
        )

    for email in firecrawl_hits:
        merge_candidate(
            RankedCandidate(
                email=email.lower(),
                confidence=FIRECRAWL_BASE_CONFIDENCE,
                reason_code="scraped",
                source_priority=SOURCE_PRIORITY["scraped"],
                pattern=infer_pattern(first_name, last_name, email, domain),
            )
        )

    for email, confidence in pattern_hits:
        merge_candidate(
            RankedCandidate(
                email=email.lower(),
                confidence=confidence,
                reason_code="pattern_derived",
                source_priority=SOURCE_PRIORITY["pattern_derived"],
                pattern=infer_pattern(first_name, last_name, email, domain),
            )
        )

    return sorted(
        ranked.values(),
        key=lambda candidate: (-candidate.confidence, candidate.source_priority, candidate.email),
    )


def infer_pattern(first_name: str, last_name: str, email: str, domain: str) -> str | None:
    local_part, _, email_domain = email.lower().partition("@")
    if _normalize_domain(email_domain) != _normalize_domain(domain):
        return None

    substitutions = _substitutions(first_name, last_name)
    if substitutions is None:
        return None

    for pattern in PATTERNS:
        if pattern.format(**substitutions) == local_part:
            return pattern

    return None


async def _safe_candidate_call(function: Any, *args: Any) -> list[str]:
    try:
        return await function(*args)
    except Exception:
        return []


def _record_verifier_call(
    db: Session,
    *,
    lookup_id: UUID,
    email: str,
    verifier_name: str,
    result: str,
    credits_used: int,
) -> None:
    db.add(
        VerifierCall(
            lookup_id=lookup_id,
            email=email,
            verifier=verifier_name,
            result=result,
            credits_used=credits_used,
        )
    )
    db.commit()


def _get_or_create_domain_pattern(db: Session, domain: str) -> DomainPattern:
    domain_pattern = db.exec(
        select(DomainPattern).where(DomainPattern.domain == domain)
    ).first()
    if domain_pattern is not None:
        return domain_pattern

    domain_pattern = DomainPattern(domain=domain)
    db.add(domain_pattern)
    db.commit()
    db.refresh(domain_pattern)
    return domain_pattern


def _update_pattern_stats(domain_pattern: DomainPattern, pattern: str, *, success: bool) -> None:
    patterns = [dict(item) for item in (domain_pattern.patterns or [])]
    pattern_index = {item.get("pattern"): idx for idx, item in enumerate(patterns)}

    if pattern in pattern_index:
        item = patterns[pattern_index[pattern]]
    else:
        item = {
            "pattern": pattern,
            "confidence": global_weight(PATTERNS.index(pattern)),
            "success_count": 0,
            "total_count": 0,
        }
        patterns.append(item)

    item["total_count"] = int(item.get("total_count", 0)) + 1
    if success:
        item["success_count"] = int(item.get("success_count", 0)) + 1
        domain_pattern.last_successful_pattern = pattern

    success_rate = 0.0
    if item["total_count"] > 0:
        success_rate = item["success_count"] / item["total_count"]
    item["confidence"] = round(global_weight(PATTERNS.index(pattern)) * success_rate, 4)

    domain_pattern.patterns = patterns
    domain_pattern.updated_at = utcnow()
    flag_modified(domain_pattern, "patterns")


def _verified_confidence(candidate_confidence: float) -> float:
    return round(min(1.0, max(0.90, candidate_confidence + 0.10)), 4)


def _substitutions(first_name: str, last_name: str) -> dict[str, str] | None:
    first_part = _normalize_name_part(first_name)
    last_part = _normalize_name_part(last_name)
    if not first_part or not last_part:
        return None

    return {
        "first": first_part,
        "last": last_part,
        "f": first_part[0],
        "l": last_part[0],
    }


def _normalize_name_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_value.lower())


def _normalize_domain(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = normalized.split("/", maxsplit=1)[0]
    return normalized.lstrip("@")
