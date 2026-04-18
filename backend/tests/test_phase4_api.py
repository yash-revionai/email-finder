import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.database import engine
from app.models.domain_pattern import DomainPattern
from app.main import app
from app.models.lookup import Lookup
from app.models.verifier_call import VerifierCall


class QueueSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def enqueue_job(self, function: str, lookup_id: str):
        self.calls.append((function, lookup_id))
        return object()


@unittest.skipUnless(
    os.getenv("RUN_POSTGRES_INTEGRATION") == "1",
    "Requires a configured PostgreSQL test database",
)
class Phase4ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.password_patcher = patch.object(settings, "app_password", "integration-password")
        self.secret_patcher = patch.object(settings, "jwt_secret", "integration-secret")
        self.password_patcher.start()
        self.secret_patcher.start()

        self.queue_spy = QueueSpy()
        app.state.redis_pool = self.queue_spy
        self.client = TestClient(app)
        self.client.__enter__()
        token_response = self.client.post("/api/auth/token", json={"password": "integration-password"})
        self.auth_headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
        with Session(engine) as session:
            session.exec(delete(VerifierCall))
            session.exec(delete(Lookup))
            session.exec(delete(DomainPattern))
            session.commit()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        app.state.redis_pool = None
        self.secret_patcher.stop()
        self.password_patcher.stop()

    def test_lookup_creation_enqueues_job(self) -> None:
        response = self.client.post(
            "/api/lookup",
            json={
                "first_name": "Jane",
                "last_name": "Doe",
                "domain": "Example.com",
            },
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(len(self.queue_spy.calls), 1)
        self.assertEqual(self.queue_spy.calls[0][0], "run_lookup")

    def test_lookup_fetch_returns_serialized_row(self) -> None:
        lookup = Lookup(
            id=uuid4(),
            first_name="John",
            last_name="Doe",
            domain="example.com",
            status="done",
            reason_code="pattern_derived",
            email="john.doe@example.com",
            confidence=0.9,
            verifier_calls_used=1,
        )
        lookup_id = lookup.id
        with Session(engine) as session:
            session.add(lookup)
            session.commit()

        response = self.client.get(f"/api/lookup/{lookup_id}", headers=self.auth_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["email"], "john.doe@example.com")
        self.assertEqual(payload["status"], "done")

    def test_history_and_analytics_endpoints_return_expected_shapes(self) -> None:
        lookup_one = Lookup(
            id=uuid4(),
            first_name="Jane",
            last_name="Doe",
            domain="example.com",
            status="done",
            reason_code="exa_found",
            email="jane.doe@example.com",
            confidence=0.95,
            verifier_calls_used=1,
        )
        lookup_two = Lookup(
            id=uuid4(),
            first_name="John",
            last_name="Smith",
            domain="other.com",
            status="done",
            reason_code="not_found",
            email=None,
            confidence=0.0,
            verifier_calls_used=2,
        )
        with Session(engine) as session:
            session.add(lookup_one)
            session.add(lookup_two)
            session.add(
                VerifierCall(
                    lookup_id=lookup_one.id,
                    email="jane.doe@example.com",
                    verifier="omniverifier",
                    result="valid",
                    credits_used=1,
                )
            )
            session.add(
                VerifierCall(
                    lookup_id=lookup_two.id,
                    email="john.smith@other.com",
                    verifier="omniverifier",
                    result="invalid",
                    credits_used=1,
                )
            )
            session.commit()

        history_response = self.client.get("/api/history?limit=10", headers=self.auth_headers)
        self.assertEqual(history_response.status_code, 200)
        history_payload = history_response.json()
        self.assertEqual(history_payload["total"], 2)
        self.assertEqual(len(history_payload["items"]), 2)

        summary_response = self.client.get("/api/analytics/summary", headers=self.auth_headers)
        self.assertEqual(summary_response.status_code, 200)
        summary_payload = summary_response.json()
        self.assertEqual(summary_payload["total_lookups"], 2)
        self.assertEqual(summary_payload["credits_used_this_month"], 2)

        volume_response = self.client.get("/api/analytics/volume", headers=self.auth_headers)
        self.assertEqual(volume_response.status_code, 200)
        self.assertEqual(len(volume_response.json()), 12)

        domains_response = self.client.get("/api/analytics/domains", headers=self.auth_headers)
        self.assertEqual(domains_response.status_code, 200)
        self.assertEqual(domains_response.json()[0]["domain"], "example.com")

        credits_response = self.client.get("/api/analytics/credits", headers=self.auth_headers)
        self.assertEqual(credits_response.status_code, 200)
        self.assertEqual(len(credits_response.json()), 12)
