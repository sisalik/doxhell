from pathlib import Path

import pytest

# Rename "Test"-prefixed models to avoid pytest trying to collect these
from doxhell.models import CoverageCollection, Requirement, RequirementsDoc, Section
from doxhell.models import Test as _Test
from doxhell.models import TestCollection as _TestCollection
from doxhell.models import TestsDoc as _TestsDoc
from doxhell.models import TestStep as _TestStep
from doxhell.reviewer import (
    ProblemCode,
    _review_coverage,
    _review_cross_references,
    _review_requirements,
    _review_tests,
)


# region Test good documentation
# Tests to ensure that given good requirements and tests, all review functions should
# return no problems.
# --------------------------------------------------------------------------------------
def test_review_good_requirements(good_reqs_doc: RequirementsDoc) -> None:
    """Reviewing a valid requirements document should return no problems."""
    problems = list(_review_requirements(good_reqs_doc))
    assert not problems


def test_review_good_tests(good_test_collection: _TestCollection) -> None:
    """Reviewing a valid test collection should return no problems."""
    problems = list(_review_tests(good_test_collection))
    assert not problems


def test_review_good_coverage(
    good_reqs_doc: RequirementsDoc, good_test_collection: _TestCollection
) -> None:
    """Reviewing a valid coverage document should return no problems."""
    coverage = _map_coverage(good_reqs_doc, good_test_collection)
    problems = list(_review_coverage(coverage))
    assert not problems


def test_review_good_cross_references(
    good_reqs_doc: RequirementsDoc, good_test_collection: _TestCollection
) -> None:
    """Reviewing valid requirements against valid tests should return no problems."""
    problems = list(_review_cross_references(good_reqs_doc, good_test_collection))
    assert not problems


# endregion

# region Test individual problem codes
# Tests to ensure that specific deficiencies are detected. Arranged by problem code,
# starting with DH001.
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("test_to_req_map", "expected_probs"),
    [
        ({0: []}, 1),  # TEST-1 verifies no reqs -> 1 problem
        ({1: []}, 0),  # TEST-2 verifies no reqs -> no problems (covered by TEST-1)
        ({0: [], 1: []}, 2),  # TEST-1 and TEST-2 verify no reqs -> 2 problems
    ],
)
def test_review_coverage_requirement_unverified(
    good_reqs_doc: RequirementsDoc,
    good_test_collection: _TestCollection,
    test_to_req_map: dict[int, list[str]],
    expected_probs: int,
) -> None:
    """DH001: All requirements must have an associated test."""
    tests = list(good_test_collection.all_tests)
    for test_id, req_ids in test_to_req_map.items():
        tests[test_id].verifies = req_ids
    coverage = _map_coverage(good_reqs_doc, good_test_collection)
    problems = list(_review_coverage(coverage))
    assert len(problems) == expected_probs
    assert all(p.code == ProblemCode.DH001 for p in problems)


@pytest.mark.parametrize(
    ("bad_requirement_idx", "expected_probs"),
    [
        ([0], 1),  # REQ-1 is obsolete with no reason -> 1 problem
        ([0, 1], 2),  # REQ-1 and REQ-2 are obsolete with no reason -> 2 problems
        ([0, 1, 2], 3),  # ...
    ],
)
def test_review_requirements_missing_obsolete_reason(
    good_reqs_doc: RequirementsDoc, bad_requirement_idx: list[int], expected_probs: int
) -> None:
    """DH002: An obsolete requirement should have a reason."""
    requirements = list(good_reqs_doc.requirements)
    for req in bad_requirement_idx:
        requirements[req].obsolete = True
        requirements[req].obsolete_reason = ""
    problems = list(_review_requirements(good_reqs_doc))
    assert len(problems) == expected_probs
    assert all(p.code == ProblemCode.DH002 for p in problems)


def test_review_cross_references_missing_requirement(
    good_reqs_doc: RequirementsDoc, good_test_collection: _TestCollection
) -> None:
    """DH003: All tests must verify requirements that exist."""
    tests = list(good_test_collection.all_tests)
    tests[0].verifies = ["REQ-X"]
    problems = list(_review_cross_references(good_reqs_doc, good_test_collection))
    assert len(problems) == 1
    assert problems[0].code == ProblemCode.DH003


@pytest.mark.parametrize(
    ("req_ids", "expected_probs"),
    [
        (["REQ-1", "REQ-1", "REQ-3", "REQ-4"], 1),  # 2 copies of REQ-1 -> 1 problem
        (["REQ-1", "REQ-1", "REQ-1", "REQ-1"], 1),  # 4 copies of REQ-1 -> 1 problem
        (["REQ-1", "REQ-1", "REQ-3", "REQ-3"], 2),  # 2 copies of 2 reqs -> 2 problems
    ],
)
def test_review_requirements_duplicate_ids(
    good_reqs_doc: RequirementsDoc, req_ids: list[str], expected_probs: int
) -> None:
    """DH004: Duplicate requirement IDs are not allowed."""
    for req_id, req in zip(req_ids, good_reqs_doc.requirements):
        req.id = req_id
    problems = list(_review_requirements(good_reqs_doc))
    assert len(problems) == expected_probs
    assert all(p.code == ProblemCode.DH004 for p in problems)


@pytest.mark.parametrize(
    ("test_ids", "expected_probs"),
    [
        (["TEST-1", "TEST-2", "TEST-2", "TEST-4"], 1),  # 2 copies of TEST-2 -> 1 prob
        (["TEST-3", "TEST-3", "TEST-3", "TEST-3"], 1),  # 4 copies of TEST-3 -> 1 prob
        (["TEST-2", "TEST-2", "TEST-4", "TEST-4"], 2),  # 2 copies of 2 tests -> 2 probs
    ],
)
def test_review_tests_duplicate_ids(
    good_test_collection: _TestCollection, test_ids: list[str], expected_probs: int
) -> None:
    """DH005: Duplicate test IDs are not allowed."""
    for test_id, test in zip(test_ids, good_test_collection.all_tests):
        test.id = test_id
    problems = list(_review_tests(good_test_collection))
    assert len(problems) == expected_probs
    assert all(p.code == ProblemCode.DH005 for p in problems)


@pytest.mark.parametrize(
    ("obsolete_reqs", "expected_probs"),
    [
        ([0], 1),  # REQ-1 is obsolete and covered by TEST-1 -> 1 problem
        ([1], 2),  # REQ-2 is obsolete and covered by TEST-1 and TEST-2 -> 2 problems
    ],
)
def test_review_coverage_test_verifies_obsolete_requirement(
    good_reqs_doc: RequirementsDoc,
    good_test_collection: _TestCollection,
    obsolete_reqs: list[int],
    expected_probs: int,
) -> None:
    """DH006: Tests must not verify obsolete requirements."""
    requirements = list(good_reqs_doc.requirements)
    for req_idx in obsolete_reqs:
        requirements[req_idx].obsolete = True
    coverage = _map_coverage(good_reqs_doc, good_test_collection)
    problems = list(_review_coverage(coverage))
    assert len(problems) == expected_probs
    assert all(p.code == ProblemCode.DH006 for p in problems)


# endregion

# region Fixtures and helpers
# Fixtures to supply good requirement and test sets, plus helper functions.
# --------------------------------------------------------------------------------------
@pytest.fixture()
def good_reqs_doc():
    """A requirements document with no problems."""
    return RequirementsDoc(
        title="Good Requirements",
        file_path=Path(),
        body=[
            Section(
                title="All Requirements",
                items=[
                    Requirement(id="REQ-1", specification="N/A", rationale="N/A"),
                    Requirement(id="REQ-2", specification="N/A", rationale="N/A"),
                    Requirement(id="REQ-3", specification="N/A", rationale="N/A"),
                    Requirement(id="REQ-4", specification="N/A", rationale="N/A"),
                ],
            ),
        ],
    )


@pytest.fixture()
def good_test_collection():
    """A test collection with no problems."""
    manual_tests_doc = _TestsDoc(
        title="Good Tests",
        file_path=Path(),
        tests=[
            _Test(
                id="TEST-1",
                description="N/A",
                verifies=["REQ-1", "REQ-2"],
                steps=[
                    _TestStep(given="A", when="B", then="C"),
                    _TestStep(given="D", when="E", then="F"),
                ],
            ),
        ],
    )
    return _TestCollection(
        automated_tests=[
            _Test(id="TEST-2", automated=True, description="N/A", verifies=["REQ-2"]),
            _Test(id="TEST-3", automated=True, description="N/A", verifies=["REQ-3"]),
            _Test(id="TEST-4", automated=True, description="N/A", verifies=["REQ-4"]),
        ],
        manual_tests_doc=manual_tests_doc,
    )


def _map_coverage(
    requirements_doc: RequirementsDoc, test_collection: _TestCollection
) -> CoverageCollection:
    """Map requirements to tests to return a coverage collection object."""
    collection = CoverageCollection()
    collection.map(requirements_doc.requirements, test_collection.all_tests)
    return collection


# endregion
