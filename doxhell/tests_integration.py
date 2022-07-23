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

    def verifies_decorator(test_function: C) -> VerificationTest[C]:
        # Cast to VerificationTest to make mypy happy
        verification_test = cast(VerificationTest[C], test_function)
        # Add requirement IDs to the test's requirement IDs, so that the decorator
        # can be used multiple times on the same test function
        requirements_list = getattr(verification_test, "requirement_ids", [])
        requirements_list.extend(requirement_ids)
        verification_test.requirement_ids = requirements_list
        return verification_test

    return verifies_decorator
