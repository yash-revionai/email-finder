from __future__ import annotations

import re
import unicodedata
from typing import Any

PATTERNS = [
    "{first}.{last}",
    "{first}{last}",
    "{f}{last}",
    "{first}",
    "{f}.{last}",
    "{first}_{last}",
    "{last}.{first}",
    "{last}{f}",
    "{first}{l}",
    "{f}{l}",
    "{last}",
    "{first}-{last}",
    "{first}.{l}",
    "{f}_{last}",
    "{last}_{first}",
]

TOP_PATTERN_CONFIDENCE = 0.70
BOTTOM_PATTERN_CONFIDENCE = 0.30
PATTERN_INDEX = {pattern: index for index, pattern in enumerate(PATTERNS)}


def global_weight(index: int) -> float:
    if index < 0 or index >= len(PATTERNS):
        raise IndexError(f"Pattern index {index} is out of range")

    if len(PATTERNS) == 1:
        return TOP_PATTERN_CONFIDENCE

    step = (TOP_PATTERN_CONFIDENCE - BOTTOM_PATTERN_CONFIDENCE) / (len(PATTERNS) - 1)
    return round(TOP_PATTERN_CONFIDENCE - (step * index), 4)


def generate_candidates(
    first: str,
    last: str,
    domain: str,
    domain_patterns_row: Any | None,
) -> list[tuple[str, float]]:
    first_part = _normalize_name_part(first)
    last_part = _normalize_name_part(last)
    domain_part = _normalize_domain(domain)

    if not first_part or not last_part or not domain_part:
        raise ValueError("first, last, and domain must all contain usable characters")

    substitutions = {
        "first": first_part,
        "last": last_part,
        "f": first_part[0],
        "l": last_part[0],
    }
    pattern_confidences = _pattern_confidences(domain_patterns_row)
    last_successful_pattern = _row_value(domain_patterns_row, "last_successful_pattern")
    ranked_candidates: dict[str, tuple[float, int, bool]] = {}

    for index, pattern in enumerate(PATTERNS):
        local_part = pattern.format(**substitutions)
        email = f"{local_part}@{domain_part}"
        confidence = pattern_confidences.get(pattern, global_weight(index))
        is_last_success = pattern == last_successful_pattern
        current = ranked_candidates.get(email)

        if current is None or confidence > current[0]:
            ranked_candidates[email] = (confidence, index, is_last_success)

    sorted_candidates = sorted(
        ranked_candidates.items(),
        key=lambda item: (-item[1][0], -int(item[1][2]), item[1][1], item[0]),
    )
    return [(email, confidence) for email, (confidence, _, _) in sorted_candidates]


def _pattern_confidences(domain_patterns_row: Any | None) -> dict[str, float]:
    stored_patterns = _row_value(domain_patterns_row, "patterns", default=[]) or []
    confidences: dict[str, float] = {}

    for item in stored_patterns:
        if not isinstance(item, dict):
            continue

        pattern = str(item.get("pattern", "")).strip()
        if pattern not in PATTERN_INDEX:
            continue

        explicit_confidence = item.get("confidence")
        if explicit_confidence is not None:
            confidences[pattern] = _clamp_confidence(explicit_confidence)
            continue

        total_count = item.get("total_count") or 0
        success_count = item.get("success_count") or 0
        if total_count <= 0:
            continue

        success_rate = max(0.0, min(1.0, float(success_count) / float(total_count)))
        confidences[pattern] = round(global_weight(PATTERN_INDEX[pattern]) * success_rate, 4)

    return confidences


def _normalize_name_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_value.lower())


def _normalize_domain(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = normalized.split("/", maxsplit=1)[0]
    return normalized.lstrip("@")


def _row_value(domain_patterns_row: Any | None, key: str, default: Any = None) -> Any:
    if domain_patterns_row is None:
        return default

    if isinstance(domain_patterns_row, dict):
        return domain_patterns_row.get(key, default)

    return getattr(domain_patterns_row, key, default)


def _clamp_confidence(value: Any) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)
