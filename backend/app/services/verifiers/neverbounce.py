from __future__ import annotations

from app.services.verifiers.base import BaseVerifier, VerifierResult


class NeverBounceVerifier(BaseVerifier):
    name = "neverbounce"

    async def verify(self, email: str) -> VerifierResult:
        raise NotImplementedError(f"{self.name} verification is not implemented yet for {email}")
