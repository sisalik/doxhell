import itertools
from typing import Iterable, List

from loguru import logger

from doxhell.loaders import Requirement, Test


def map_coverage(requirements: Iterable[Requirement], tests: Iterable[Test]) -> None:
    """Map coverage between requirements and tests."""
    for requirement, test in itertools.product(requirements, tests):
        if requirement.id in test.requirement_ids:
            requirement.tests.append(test)
            test.requirements.append(requirement)
            logger.info("{} tested by {}", requirement.id, test.id)


def check_coverage(requirements: Iterable[Requirement]) -> List[str]:
    """Check for requirements without tests."""
    problems = []
    for requirement in requirements:
        if not requirement.tests:
            problem_msg = f"{requirement.id} has no tests"
            problems.append(problem_msg)
            logger.error(problem_msg)
    return problems


def check_undefined_requirements(tests: Iterable[Test]) -> List[str]:
    """Check for tests that reference non-existent requirements."""
    problems = []
    for test in tests:
        valid_requirement_ids = {req.id for req in test.requirements}
        for req_id in set(test.requirement_ids) - valid_requirement_ids:
            problem_msg = f"{test.id} references non-existent requirement {req_id}"
            problems.append(problem_msg)
            logger.warning(problem_msg)
    return problems
