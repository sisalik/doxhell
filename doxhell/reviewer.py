import dataclasses
import enum
import itertools
from typing import Iterable, List, Tuple

from loguru import logger

import doxhell.loaders
from doxhell.loaders import Requirement, Test


@dataclasses.dataclass
class Problem:
    """A problem found in the documentation."""

    description: str
    severity: "Severity"

    def __str__(self):
        return self.description


class Severity(str, enum.Enum):
    """The severity of a problem."""

    HIGH = "HIGH"
    MEDIUM = "MED"
    LOW = "LOW"


def review(
    test_dirs: Tuple[str, ...], docs_dirs: Tuple[str, ...]
) -> Tuple[List[Requirement], List[Test], List[Problem]]:
    """Validate requirements and tests; check coverage."""
    # Load all requirements and tests and convert to lists since we need to iterate
    # over them multiple times
    requirements = list(doxhell.loaders.load_requirements(docs_dirs))
    if not requirements:
        raise ValueError(f"No requirements found in directories {docs_dirs}")
    tests = list(doxhell.loaders.load_tests(docs_dirs, test_dirs))

    _map_coverage(requirements, tests)
    problems = _check_coverage(requirements) + _check_undefined_requirements(tests)
    return requirements, tests, problems


def _map_coverage(requirements: Iterable[Requirement], tests: Iterable[Test]) -> None:
    """Map coverage between requirements and tests."""
    for requirement, test in itertools.product(requirements, tests):
        if requirement.id in test.requirement_ids:
            requirement.tests.append(test)
            test.requirements.append(requirement)
            logger.debug("{} tested by {}", requirement.id, test.id)


def _check_coverage(requirements: Iterable[Requirement]) -> List[Problem]:
    """Check for requirements without tests."""
    problems = []
    for requirement in requirements:
        if not requirement.tests:
            problem = Problem(f"{requirement.id} has no tests", Severity.HIGH)
            problems.append(problem)
            logger.debug(problem)
    return problems


def _check_undefined_requirements(tests: Iterable[Test]) -> List[Problem]:
    """Check for tests that reference non-existent requirements."""
    problems = []
    for test in tests:
        valid_requirement_ids = {req.id for req in test.requirements}
        for req_id in set(test.requirement_ids) - valid_requirement_ids:
            problem = Problem(
                f"{test.id} references non-existent requirement {req_id}",
                Severity.MEDIUM,
            )
            problems.append(problem)
            logger.debug(problem)
    return problems
