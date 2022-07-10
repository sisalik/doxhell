from typing import Any, Callable, List, Protocol


class TestFunction(Protocol):
    """Type hint for test functions."""

    requirement_ids: List[str]

    def __name__(self) -> str:
        ...


def verifies(*requirement_ids: str) -> Callable[[Any], TestFunction]:
    """Decorator to mark test functions as verifying a requirement."""

    def satisfies_decorator(test_function: Any) -> TestFunction:
        test_function.requirement_ids = list(requirement_ids)
        return test_function

    return satisfies_decorator
