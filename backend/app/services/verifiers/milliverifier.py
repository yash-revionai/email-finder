from __future__ import annotations

from app.services.verifiers.base import BaseVerifier, VerifierResult


class MilliVerifier(BaseVerifier):
    name = "milliverifier"

    async def verify(self, email: str) -> VerifierResult:
        raise NotImplementedError(f"{self.name} verification is not implemented yet for {email}")
