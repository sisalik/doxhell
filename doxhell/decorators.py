from collections.abc import Callable
from typing import Protocol, TypeVar, cast, runtime_checkable

C = TypeVar("C", bound=Callable)


@runtime_checkable
class VerificationTest(Protocol[C]):
    """Protocol of any callable that acts as a verification test."""

    requirement_ids: list[str]

    __call__: C


def verifies(*requirement_ids: str) -> Callable[[C], VerificationTest[C]]:
    """Decorator to mark test functions as verifying a requirement."""

    def satisfies_decorator(test_function: C) -> VerificationTest[C]:
        # Cast to VerificationTest to make mypy happy
        verification_test = cast(VerificationTest[C], test_function)
        verification_test.requirement_ids = list(requirement_ids)
        return verification_test

    return satisfies_decorator
