import dataclasses
import enum
import itertools
from pathlib import Path

from loguru import logger

import doxhell.loaders
from doxhell.loaders import RequirementsDoc, TestSuite


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
    test_dirs: tuple[Path, ...], docs_dirs: tuple[Path, ...]
) -> tuple[RequirementsDoc, TestSuite, list[Problem]]:
    """Validate requirements and tests; check coverage."""
    requirements = doxhell.loaders.load_requirements(docs_dirs)
    tests = doxhell.loaders.load_tests(docs_dirs, test_dirs)

    _map_coverage(requirements, tests)
    problems = _check_coverage(requirements) + _check_undefined_requirements(tests)
    return requirements, tests, problems


def _map_coverage(requirement_spec: RequirementsDoc, test_suite: TestSuite) -> None:
    """Map coverage between requirements and tests."""
    for requirement, test in itertools.product(
        requirement_spec.requirements, test_suite.all_tests
    ):
        if requirement.id in test.verifies:
            requirement.tests.append(test)
            test.requirements.append(requirement)


def _check_coverage(requirement_spec: RequirementsDoc) -> list[Problem]:
    """Check for requirements without tests."""
    problems = []
    for requirement in requirement_spec.requirements:
        if not requirement.tests:
            problem = Problem(f"{requirement.id} has no tests", Severity.HIGH)
            problems.append(problem)
            logger.debug(problem)
    return problems


def _check_undefined_requirements(test_suite: TestSuite) -> list[Problem]:
    """Check for tests that reference non-existent requirements."""
    problems = []
    for test in test_suite.all_tests:
        valid_requirement_ids = {req.id for req in test.requirements}
        for req_id in set(test.verifies) - valid_requirement_ids:
            problem = Problem(
                f"{test.id} references non-existent requirement {req_id}",
                Severity.MEDIUM,
            )
            problems.append(problem)
            logger.debug(problem)
    return problems
