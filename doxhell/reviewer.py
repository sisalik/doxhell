import dataclasses
import enum
import itertools
from collections import Counter
from pathlib import Path
from typing import Iterator

from loguru import logger

import doxhell.loaders
from doxhell.loaders import Requirement, RequirementsDoc, Test, TestSuite


class ProblemCode(int, enum.Enum):
    """Code for a particular problem type."""

    DH001 = 1  # Requirement has no tests
    DH002 = 2  # Requirement is marked obsolete without a reason given
    DH003 = 3  # Test references a non-existent requirement
    DH004 = 4  # Requirement has a duplicate identifier
    DH005 = 5  # Test has a duplicate identifier


@dataclasses.dataclass
class Problem:
    """A problem found in the documentation."""

    description: str
    code: ProblemCode

    def __str__(self):
        return self.description


def review(
    test_dirs: tuple[Path, ...],
    docs_dirs: tuple[Path, ...],
    ignores: tuple[ProblemCode, ...],
) -> tuple[RequirementsDoc, TestSuite, list[Problem]]:
    """Validate requirements and tests; check coverage."""
    requirements = doxhell.loaders.load_requirements(docs_dirs)
    tests = doxhell.loaders.load_tests(docs_dirs, test_dirs)

    _map_coverage(requirements, tests)
    problems = itertools.chain(_review_requirements(requirements), _review_tests(tests))
    problems_not_ignored = filter(lambda p: p.code not in ignores, problems)
    return requirements, tests, list(problems_not_ignored)


def _map_coverage(requirement_spec: RequirementsDoc, test_suite: TestSuite) -> None:
    """Map coverage between requirements and tests."""
    for requirement, test in itertools.product(
        requirement_spec.requirements, test_suite.all_tests
    ):
        if requirement.id in test.verifies:
            requirement.tests.append(test)
            test.requirements.append(requirement)


def _review_requirements(requirement_spec: RequirementsDoc) -> Iterator[Problem]:
    """Review requirements for various problems."""
    # Run check functions that operate on single requirements
    for requirement in requirement_spec.requirements:
        yield from itertools.chain(
            _check_coverage(requirement),
            _check_missing_obsolete_reason(requirement),
        )
    # Run check functions that operate on the entire set of requirements
    yield from _check_requirement_ids_are_unique(requirement_spec)


def _review_tests(test_suite: TestSuite) -> Iterator[Problem]:
    """Review tests for various problems."""
    # Run check functions that operate on single tests
    for test in test_suite.all_tests:
        yield from _check_undefined_requirements(test)
    # Run check functions that operate on the entire set of tests
    yield from _check_test_ids_are_unique(test_suite)


def _check_coverage(requirement: Requirement) -> Iterator[Problem]:
    """Check for requirements without tests."""
    if not requirement.tests and not requirement.obsolete:
        problem = Problem(f"{requirement.id} has no tests", ProblemCode.DH001)
        logger.debug(problem)
        yield problem


def _check_missing_obsolete_reason(requirement: Requirement) -> Iterator[Problem]:
    """Check for requirements made obsolete without a reason."""
    if requirement.obsolete and not requirement.obsolete_reason:
        problem = Problem(
            f"{requirement.id} is marked obsolete without a reason given",
            ProblemCode.DH002,
        )
        logger.debug(problem)
        yield problem


def _check_requirement_ids_are_unique(
    requirement_spec: RequirementsDoc,
) -> Iterator[Problem]:
    """Check for duplicate requirement identifiers."""
    id_counter: Counter = Counter()
    for requirement in requirement_spec.requirements:
        id_counter[requirement.id] += 1
    # Find requirement IDs that appear more than once
    duplicate_ids = filter(lambda c: c[1] > 1, id_counter.items())
    for id, count in duplicate_ids:
        problem = Problem(
            f"Requirement {id} is defined {count} times", ProblemCode.DH004
        )
        logger.debug(problem)
        yield problem


def _check_test_ids_are_unique(test_suite: TestSuite) -> Iterator[Problem]:
    """Check for duplicate test identifiers."""
    id_counter: Counter = Counter()
    for test in test_suite.all_tests:
        id_counter[test.id] += 1
    # Find test IDs that appear more than once
    duplicate_ids = filter(lambda c: c[1] > 1, id_counter.items())
    for id, count in duplicate_ids:
        problem = Problem(f"Test {id} is defined {count} times", ProblemCode.DH005)
        logger.debug(problem)
        yield problem


def _check_undefined_requirements(test: Test) -> Iterator[Problem]:
    """Check for tests that reference non-existent requirements."""
    valid_requirement_ids = {req.id for req in test.requirements}
    for req_id in set(test.verifies) - valid_requirement_ids:
        problem = Problem(
            f"Test {test.id} references non-existent requirement {req_id}",
            ProblemCode.DH003,
        )
        logger.debug(problem)
        yield problem
