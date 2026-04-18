import json
import unittest

import httpx

from app.services.exa_searcher import search_email
from app.services.firecrawl_scraper import scrape_domain_patterns
from app.services.verifiers.omniverifier import OmniVerifier


class OmniVerifierTests(unittest.IsolatedAsyncioTestCase):
    async def test_verify_maps_valid_status(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/v1/validate/email/check")
            self.assertEqual(request.headers["x-api-key"], "test-key")
            self.assertEqual(request.read(), b'{"email":"user@example.com"}')
            return httpx.Response(
                200,
                json={"status": "valid", "mail_server": "outlook.com"},
                request=request,
            )

        client = httpx.AsyncClient(
            base_url="https://api.omniverifier.com",
            transport=httpx.MockTransport(handler),
        )
        verifier = OmniVerifier(api_key="test-key", http_client=client)

        try:
            result = await verifier.verify("user@example.com")
        finally:
            await client.aclose()

        self.assertEqual(result.result, "valid")
        self.assertEqual(result.reason, "valid")
        self.assertEqual(result.credits_used, 1)

    async def test_verify_raises_on_api_error(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": "Invalid API key", "code": "INVALID_API_KEY"},
                request=request,
            )

        client = httpx.AsyncClient(
            base_url="https://api.omniverifier.com",
            transport=httpx.MockTransport(handler),
        )
        verifier = OmniVerifier(api_key="bad-key", http_client=client)

        try:
            with self.assertRaises(RuntimeError):
                await verifier.verify("user@example.com")
        finally:
            await client.aclose()


class ExaSearcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_email_extracts_matching_domain_emails(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/search")
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Team",
                            "text": "Reach Jane at jane.doe@example.com for sales.",
                            "highlights": ["CEO: jane.doe@example.com"],
                        },
                        {
                            "summary": "Alternate alias: jdoe@example.com",
                            "url": "https://example.com/about",
                        },
                        {
                            "text": "Ignore user@other.com because it is off-domain.",
                        },
                    ]
                },
                request=request,
            )

        client = httpx.AsyncClient(
            base_url="https://api.exa.ai",
            transport=httpx.MockTransport(handler),
        )

        try:
            emails = await search_email(
                "Jane",
                "Doe",
                "example.com",
                api_key="exa-key",
                http_client=client,
            )
        finally:
            await client.aclose()

        self.assertEqual(emails, ["jane.doe@example.com", "jdoe@example.com"])


class FirecrawlScraperTests(unittest.IsolatedAsyncioTestCase):
    async def test_scrape_domain_patterns_extracts_matching_emails(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            path = json.loads(request.content.decode("utf-8"))["url"]
            emails_by_path = {
                "https://example.com/team": "Team: jane.doe@example.com",
                "https://example.com/about": "Leadership: jdoe@example.com",
                "https://example.com/contact": "Support: help@other.com",
            }
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "markdown": emails_by_path[path],
                    },
                },
                request=request,
            )

        client = httpx.AsyncClient(
            base_url="https://api.firecrawl.dev/v2",
            transport=httpx.MockTransport(handler),
        )

        try:
            emails = await scrape_domain_patterns(
                "example.com",
                api_key="fc-key",
                http_client=client,
            )
        finally:
            await client.aclose()

        self.assertEqual(emails, ["jane.doe@example.com", "jdoe@example.com"])
