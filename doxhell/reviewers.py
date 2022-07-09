import itertools
from typing import Iterable, List

from loguru import logger

from doxhell.loaders import Requirement, Test
from doxhell.outputs import Problem, Severity


def map_coverage(requirements: Iterable[Requirement], tests: Iterable[Test]) -> None:
    """Map coverage between requirements and tests."""
    for requirement, test in itertools.product(requirements, tests):
        if requirement.id in test.requirement_ids:
            requirement.tests.append(test)
            test.requirements.append(requirement)
            logger.debug("{} tested by {}", requirement.id, test.id)


def check_coverage(requirements: Iterable[Requirement]) -> List[Problem]:
    """Check for requirements without tests."""
    problems = []
    for requirement in requirements:
        if not requirement.tests:
            problem = Problem(f"{requirement.id} has no tests", Severity.HIGH)
            problems.append(problem)
            logger.debug(problem)
    return problems


def check_undefined_requirements(tests: Iterable[Test]) -> List[Problem]:
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
