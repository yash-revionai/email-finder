from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class VerifierResult:
    result: str
    reason: str
    credits_used: int = 1


class BaseVerifier(ABC):
    name = "base"

    @abstractmethod
    async def verify(self, email: str) -> VerifierResult:
        raise NotImplementedError
