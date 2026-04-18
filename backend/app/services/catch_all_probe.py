from __future__ import annotations

import secrets
import smtplib
import socket
from contextlib import suppress

import dns.resolver
from sqlmodel import Session, select

from app.core.database import engine
from app.models.base import utcnow
from app.models.domain_pattern import DomainPattern

SMTP_ACCEPT_CODES = {250, 251}
SMTP_REJECT_CODES = {550, 551, 552, 553, 554}


def is_catch_all(domain: str, session: Session | None = None, timeout: float = 5.0) -> bool:
    normalized_domain = _normalize_domain(domain)
    owns_session = session is None
    db = session or Session(engine)

    try:
        pattern_row = db.exec(
            select(DomainPattern).where(DomainPattern.domain == normalized_domain)
        ).first()
        if pattern_row and pattern_row.is_catch_all is not None:
            return pattern_row.is_catch_all

        probe_result = probe_catch_all_status(normalized_domain, timeout=timeout)
        if probe_result is not None:
            _cache_probe_result(db, normalized_domain, probe_result, pattern_row)

        return bool(probe_result)
    finally:
        if owns_session:
            db.close()


def probe_catch_all_status(domain: str, timeout: float = 5.0) -> bool | None:
    recipient = f"{secrets.token_hex(12)}@{_normalize_domain(domain)}"

    for mail_host in _resolve_mail_hosts(domain, timeout=timeout):
        result = _probe_mail_host(mail_host, recipient, timeout=timeout)
        if result is not None:
            return result

    return None


def _cache_probe_result(
    session: Session,
    domain: str,
    is_catch_all_result: bool,
    pattern_row: DomainPattern | None,
) -> None:
    row = pattern_row or DomainPattern(domain=domain)
    row.is_catch_all = is_catch_all_result
    row.updated_at = utcnow()
    session.add(row)
    session.commit()


def _resolve_mail_hosts(domain: str, timeout: float) -> list[str]:
    normalized_domain = _normalize_domain(domain)
    resolver = dns.resolver.Resolver(configure=True)
    resolver.timeout = timeout
    resolver.lifetime = timeout

    with suppress(
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.resolver.LifetimeTimeout,
    ):
        answers = resolver.resolve(normalized_domain, "MX")
        ordered_answers = sorted(answers, key=lambda answer: answer.preference)
        hosts = [str(answer.exchange).rstrip(".") for answer in ordered_answers]
        if hosts:
            return hosts

    return [normalized_domain]


def _probe_mail_host(host: str, recipient: str, timeout: float) -> bool | None:
    sender_domain = socket.getfqdn().strip() or "localhost.localdomain"
    if "." not in sender_domain:
        sender_domain = "localhost.localdomain"

    with suppress(OSError, smtplib.SMTPException):
        with smtplib.SMTP(host=host, port=25, timeout=timeout) as smtp:
            smtp.ehlo_or_helo_if_needed()

            mail_code, _ = smtp.mail(f"catchall-probe@{sender_domain}")
            if mail_code not in SMTP_ACCEPT_CODES:
                return None

            rcpt_code, _ = smtp.rcpt(recipient)
            if rcpt_code in SMTP_ACCEPT_CODES:
                return True
            if rcpt_code in SMTP_REJECT_CODES:
                return False

    return None


def _normalize_domain(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.removeprefix("https://").removeprefix("http://")
    normalized = normalized.split("/", maxsplit=1)[0]
    return normalized.lstrip("@")
