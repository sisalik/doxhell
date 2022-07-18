from collections.abc import Callable
from typing import Any


def verifies(*requirement_ids: str) -> Callable[[Any], Callable]:
    """Decorator to mark test functions as verifying a requirement."""

    def satisfies_decorator(test_function: Any) -> Callable:
        test_function.requirement_ids = list(requirement_ids)
        return test_function

    return satisfies_decorator
