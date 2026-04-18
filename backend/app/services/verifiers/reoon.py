from __future__ import annotations

from app.services.verifiers.base import BaseVerifier, VerifierResult


class ReoonVerifier(BaseVerifier):
    name = "reoon"

    async def verify(self, email: str) -> VerifierResult:
        raise NotImplementedError(f"{self.name} verification is not implemented yet for {email}")
