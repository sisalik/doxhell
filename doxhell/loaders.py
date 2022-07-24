import inspect
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import yaml
from loguru import logger
from pydantic import ValidationError

import doxhell.utils
from doxhell.models import (
    CoverageCollection,
    CoverageDoc,
    Requirement,
    RequirementsDoc,
    Section,
    Test,
    TestCollection,
    TestsDoc,
)
from doxhell.tests_integration import VerificationTest


def load_requirements(docs_root_dirs: Iterable[Path]) -> RequirementsDoc:
    """Load a requirements document from the given paths."""
    requirements_docs = list(_load_all_requirements_docs(docs_root_dirs))
    if not requirements_docs:
        raise ValueError(f"No requirements docs found in directories {docs_root_dirs}")
    elif len(requirements_docs) > 1:
        file_paths = "; ".join(str(r.file_path) for r in requirements_docs)
        raise ValueError(f"Multiple requirements docs found: {file_paths}")
    return requirements_docs[0]


def load_tests(
    docs_root_dirs: Iterable[Path], test_root_dirs: Iterable[Path]
) -> TestCollection:
    """Load all manual and automated tests from the given paths."""
    manual_test_docs = list(_load_all_manual_test_docs(docs_root_dirs))
    # You can have a valid test suite with no manual tests, but multiple protocol files
    # are not supported
    if len(manual_test_docs) > 1:
        file_paths = "; ".join(str(r.file_path) for r in manual_test_docs)
        raise ValueError(f"Multiple manual test protocols found: {file_paths}")

    automated_tests = list(_load_all_automated_tests(test_root_dirs))
    return TestCollection(
        manual_tests_doc=manual_test_docs[0] if manual_test_docs else None,
        automated_tests=automated_tests,
    )


def load_coverage(docs_root_dirs: Iterable[Path]) -> CoverageCollection:
    """Load a coverage document from the given paths."""
    coverage_docs = list(_load_all_coverage_docs(docs_root_dirs))
    if len(coverage_docs) > 1:
        file_paths = "; ".join(str(r.file_path) for r in coverage_docs)
        raise ValueError(f"Multiple coverage docs found: {file_paths}")
    return CoverageCollection(coverage_doc=coverage_docs[0] if coverage_docs else None)


def _load_all_requirements_docs(
    docs_root_dirs: Iterable[Path],
) -> Iterator[RequirementsDoc]:
    """Load all requirements documents from the given paths."""
    for docs_root_dir in set(docs_root_dirs):  # Ignore duplicate directories
        logger.info("Looking for requirements docs in {}", docs_root_dir)
        for item in docs_root_dir.rglob("requirements.y*ml"):
            logger.debug("Found requirements file: {}", item)
            yield _load_requirements_document(item)


def _load_all_manual_test_docs(docs_root_dirs: Iterable[Path]) -> Iterator[TestsDoc]:
    """Load all manual test protocols from the given paths."""
    for docs_root_dir in set(docs_root_dirs):  # Ignore duplicate directories
        logger.info("Looking for manual tests in {}", docs_root_dir)
        for item in docs_root_dir.rglob("tests.y*ml"):
            logger.debug("Found test protocol file: {}", item)
            yield _load_test_protocol(item)


def _load_all_coverage_docs(docs_root_dirs: Iterable[Path]) -> Iterator[CoverageDoc]:
    """Load all coverage documents from the given paths."""
    for docs_root_dir in set(docs_root_dirs):  # Ignore duplicate directories
        logger.info("Looking for coverage docs in {}", docs_root_dir)
        for item in docs_root_dir.rglob("coverage.y*ml"):
            logger.debug("Found coverage file: {}", item)
            yield _load_coverage_document(item)


def _load_all_automated_tests(test_root_dirs: Iterable[Path]) -> Iterator[Test]:
    """Load all automated tests from the given paths."""
    for test_root_dir in set(test_root_dirs):  # Ignore duplicate directories
        logger.info("Looking for tests in {}", test_root_dir)

        for test_file in _find_test_files(test_root_dir):
            for test_function in _find_test_functions(test_file):
                # Check if the test function has been decorated with @verifies
                if not isinstance(test_function, VerificationTest):
                    continue
                yield Test(
                    id=test_function.__name__,
                    description=str(test_function.__doc__),
                    verifies=test_function.requirement_ids,
                    automated=True,
                    file_path=test_file,
                )


def _load_requirements_document(file_path: Path) -> RequirementsDoc:
    """Load the requirements specification from the given YAML file."""
    with open(file_path) as file:
        yaml_content = file.read()
    data = yaml.safe_load(yaml_content)
    try:
        requirements_doc = RequirementsDoc(file_path=file_path, **data)
    except ValidationError:
        logger.error("Error parsing requirements file: {}", file_path)
        raise
    # If the document has no sections and is a flat list of requirements, create
    # a default section to group all requirements
    if isinstance(requirements_doc.body[0], Requirement):
        requirements_doc.body = [
            Section(title="Requirements", items=requirements_doc.body)
        ]
    return requirements_doc


def _load_test_protocol(file_path: Path) -> TestsDoc:
    """Load the test protocol from the given YAML file."""
    with open(file_path) as file:
        yaml_content = file.read()
    data = yaml.safe_load(yaml_content)
    try:
        tests_doc = TestsDoc(file_path=file_path, **data)
    except ValidationError:
        logger.error("Error parsing test protocol file: {}", file_path)
        raise
    # Populate file_path for each Test
    for test in tests_doc.tests:
        test.file_path = file_path
    return tests_doc


def _load_coverage_document(file_path: Path) -> CoverageDoc:
    """Load the coverage document from the given YAML file."""
    with open(file_path) as file:
        yaml_content = file.read()
    data = yaml.safe_load(yaml_content)
    try:
        coverage_doc = CoverageDoc(file_path=file_path, **data)
    except ValidationError:
        logger.error("Error parsing coverage file: {}", file_path)
        raise
    return coverage_doc


def _find_test_files(path: Path) -> Iterator[Path]:
    """Find all automated test files in the given path."""
    for item in path.iterdir():
        # Skip hidden files/directories
        if item.name.startswith("."):
            continue
        # If item is a directory, recurse into it
        if item.is_dir():
            yield from _find_test_files(item)
        # Skip non-Python files
        if item.suffix != ".py":
            continue
        # Find test modules the same way as pytest, as per:
        # https://docs.pytest.org/en/latest/explanation/goodpractices.html#conventions-for-python-test-discovery
        if item.stem.startswith("test_") or item.stem.endswith("_test"):
            logger.debug("Found test file: {}", item)
            yield item


def _find_test_functions(file_path: Path) -> Iterator[Callable]:
    """Find all test functions in the given module."""
    module = doxhell.utils.import_module(file_path)
    for name, obj in inspect.getmembers(module):
        # As per pytest test discovery method:
        # 1. Look for "test" prefixed test functions or methods outside of classes
        if name.startswith("test") and inspect.isfunction(obj):
            logger.debug(f"Found test function: {name}")
            yield obj
        # 2. Look for "test" prefixed test functions or methods inside "Test" prefixed
        # test classes (without an __init__ method)
        elif (
            name.startswith("Test")
            and inspect.isclass(obj)
            and "__init__" not in obj.__dict__
        ):
            logger.debug(f"Found test class: {name}")
            for member_name, member_obj in inspect.getmembers(obj):
                if member_name.startswith("test") and inspect.isfunction(member_obj):
                    logger.debug(f"Found test method: {member_name}")
                    yield member_obj
