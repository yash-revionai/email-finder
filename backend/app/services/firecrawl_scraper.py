from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from app.core.config import settings

EMAIL_PATTERN = re.compile(r"\b[a-z0-9._%+\-]+@([a-z0-9.\-]+\.[a-z]{2,})\b", re.IGNORECASE)
SCRAPE_PATHS = ("/team", "/about", "/contact")


async def scrape_domain_patterns(
    domain: str,
    *,
    api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[str]:
    resolved_api_key = api_key or settings.firecrawl_api_key
    if not resolved_api_key:
        raise ValueError("FIRECRAWL_API_KEY is not configured")

    normalized_domain = _normalize_domain(domain)
    headers = {
        "Authorization": f"Bearer {resolved_api_key}",
        "Content-Type": "application/json",
    }
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(
        base_url=settings.firecrawl_base_url,
        timeout=settings.firecrawl_timeout_seconds,
    )

    try:
        tasks = [
            _scrape_single_page(client, headers, normalized_domain, path)
            for path in SCRAPE_PATHS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        seen: set[str] = set()
        ordered_matches: list[str] = []

        for result in results:
            if isinstance(result, Exception):
                continue

            for email in result:
                if email not in seen:
                    seen.add(email)
                    ordered_matches.append(email)

        return ordered_matches
    finally:
        if owns_client:
            await client.aclose()


async def _scrape_single_page(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    domain: str,
    path: str,
) -> list[str]:
    payload = {
        "url": f"https://{domain}{path}",
        "formats": ["markdown", "html"],
        "onlyMainContent": True,
        "maxAge": 172800000,
        "timeout": int(settings.firecrawl_timeout_seconds * 1000),
        "blockAds": True,
    }
    response = await client.post("/scrape", json=payload, headers=headers)

    if response.status_code >= 400:
        raise RuntimeError(f"Firecrawl scrape failed for {path}: {response.text}")

    body = response.json()
    if not body.get("success", False):
        raise RuntimeError(f"Firecrawl scrape failed for {path}: {body}")

    data = body.get("data", {})
    return _extract_candidate_emails(data, domain)


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
