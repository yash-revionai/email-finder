from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.config import settings

EMAIL_PATTERN = re.compile(r"\b[a-z0-9._%+\-]+@([a-z0-9.\-]+\.[a-z]{2,})\b", re.IGNORECASE)


async def search_email(
    first: str,
    last: str,
    domain: str,
    *,
    api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
    num_results: int = 5,
) -> list[str]:
    resolved_api_key = api_key or settings.exa_api_key
    if not resolved_api_key:
        raise ValueError("EXA_API_KEY is not configured")

    normalized_domain = _normalize_domain(domain)
    query = f'"{first.strip()} {last.strip()}" "@{normalized_domain}"'
    payload = {
        "query": query,
        "type": "auto",
        "numResults": num_results,
        "contents": {
            "highlights": {
                "maxCharacters": 2000,
            }
        },
    }
    headers = {
        "x-api-key": resolved_api_key,
        "Content-Type": "application/json",
    }
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(
        base_url=settings.exa_base_url,
        timeout=settings.exa_timeout_seconds,
    )

    try:
        response = await client.post("/search", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return _extract_candidate_emails(data, normalized_domain)
    finally:
        if owns_client:
            await client.aclose()


def _extract_candidate_emails(payload: Any, domain: str) -> list[str]:
    seen: set[str] = set()
    ordered_matches: list[str] = []

    for value in _walk_values(payload):
        if not isinstance(value, str):
            continue

        for email in _extract_emails_from_text(value, domain):
            if email not in seen:
                seen.add(email)
                ordered_matches.append(email)

    return ordered_matches


def _walk_values(value: Any) -> list[Any]:
    stack = [value]
    flattened: list[Any] = []

    while stack:
        current = stack.pop()
        flattened.append(current)

        if isinstance(current, dict):
            stack.extend(reversed(list(current.values())))
        elif isinstance(current, list):
            stack.extend(reversed(current))

    return flattened


def _extract_emails_from_text(text: str, domain: str) -> list[str]:
    matches: list[str] = []
    normalized_domain = _normalize_domain(domain)

    for match in EMAIL_PATTERN.finditer(text):
        email = match.group(0).lower()
        if _normalize_domain(match.group(1)) == normalized_domain:
            matches.append(email)

    return matches


def _normalize_domain(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.removeprefix("https://").removeprefix("http://")
    normalized = normalized.split("/", maxsplit=1)[0]
    return normalized.lstrip("@")
