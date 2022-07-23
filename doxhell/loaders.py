import enum
import importlib
import inspect
import unittest.mock
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from types import ModuleType

import yaml
from loguru import logger
from pydantic import BaseModel, ValidationError, validator

from doxhell.tests_integration import VerificationTest


class HashableBaseModel(BaseModel):
    """Base model that can be used as a hashable key."""

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))


class Requirement(HashableBaseModel):
    """A requirement found in the documentation."""

    id: str
    specification: str
    rationale: str
    parent: str = ""
    obsolete: bool = False
    obsolete_reason: str = ""


class EvidenceType(str, enum.Enum):
    """The type of evidence used to prove that a manual test passed."""

    SCREENSHOT = "screenshot"
    LOG = "log"
    OBSERVATION = "observation"
    SETTINGS = "settings"


class TestStep(BaseModel):
    """A step in a test."""

    given: str
    when: str
    then: str
    evidence: EvidenceType | None


class Test(BaseModel):
    """A test found in the documentation or automated test module."""

    id: str
    description: str
    verifies: list[str]
    steps: list[TestStep] = []
    automated: bool = False
    file_path: Path | None

    @validator("automated", always=True)
    def steps_must_be_defined_for_manual_test(cls, v, values):
        """Validate that steps are defined if automated is False."""
        if not v and not values["steps"]:
            raise ValueError("steps are required for a manual test")
        return v

    @property
    def full_name(self) -> str:
        """Return the full name of the test."""
        return f"{self.file_path}::{self.id}"


class Section(BaseModel):
    """A section in a document."""

    title: str
    items: list[Requirement]


class BaseDocument(BaseModel):
    """A base class for a document."""

    title: str
    number: str | None
    revision: str | None
    author: str | None
    file_path: Path

    @property
    def full_title(self) -> str:
        """Return the full name of the document."""
        title = ""
        if self.number:
            title += self.number
        if self.revision:
            title += self.revision
        if self.number or self.revision:
            title += " "
        title += self.title
        return title


class RequirementsDoc(BaseDocument):
    """A requirements specification document."""

    # When parsing documents, support a flat list of requirements or a list of sections,
    # each containing a list of requirements. In the former case, they will be grouped
    # under a default section during loading.
    body: list[Requirement] | list[Section]

    @property
    def requirements(self) -> Iterator[Requirement]:
        """Yield all requirements."""
        for section in self.body:
            # By this point, a flat list of requirements must be grouped under a section
            assert isinstance(section, Section), "body must be a list of sections"
            yield from section.items


class CoverageDoc(BaseDocument):
    """A test coverage document."""

    # Mapping of requirements to test populated during later review, not initial parsing
    mapping: dict[Requirement, list[Test]] = {}

    def map(self, requirements: Iterable[Requirement], tests: Iterable[Test]) -> None:
        """Map requirements to tests."""
        tests_list = list(tests)  # If an iterator is passed, it will be consumed
        for requirement in requirements:
            self.mapping[requirement] = []
            for test in tests_list:
                if requirement.id in test.verifies:
                    self.mapping[requirement].append(test)


class TestsDoc(BaseDocument):
    """A manual test protocol document."""

    tests: list[Test]


class TestSuite(BaseModel):
    """A collection of automated and manual tests."""

    manual_tests_doc: TestsDoc | None
    automated_tests: list[Test]

    @property
    def all_tests(self) -> Iterator[Test]:
        """Yield all tests."""
        if self.manual_tests_doc:
            yield from self.manual_tests_doc.tests
        if self.automated_tests:
            yield from self.automated_tests


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
) -> TestSuite:
    """Load all manual and automated tests from the given paths."""
    manual_test_docs = list(_load_all_manual_test_docs(docs_root_dirs))
    # You can have a valid test suite with no manual tests, but multiple protocol files
    # are not supported
    if len(manual_test_docs) > 1:
        file_paths = "; ".join(str(r.file_path) for r in manual_test_docs)
        raise ValueError(f"Multiple manual test protocols found: {file_paths}")

    automated_tests = list(_load_all_automated_tests(test_root_dirs))
    return TestSuite(
        manual_tests_doc=manual_test_docs[0] if manual_test_docs else None,
        automated_tests=automated_tests,
    )


def load_coverage(docs_root_dirs: Iterable[Path]) -> CoverageDoc:
    """Load a coverage document from the given paths."""
    coverage_docs = list(_load_all_coverage_docs(docs_root_dirs))
    if not coverage_docs:
        raise ValueError(f"No coverage docs found in directories {docs_root_dirs}")
    elif len(coverage_docs) > 1:
        file_paths = "; ".join(str(r.file_path) for r in coverage_docs)
        raise ValueError(f"Multiple coverage docs found: {file_paths}")
    return coverage_docs[0]


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
    module = _import_module(file_path)
    # TODO: Support unittest style test classes
    for name, obj in inspect.getmembers(module):
        if name.startswith("test") and inspect.isfunction(obj):
            yield obj


def _import_module(file_path: Path) -> ModuleType:
    """Import the given module, without having the module dependencies installed.

    We need to be able to import test modules without having the project dependencies
    installed. This is because doxhell may be installed in an environment outside of the
    project.

    Normally, imports of any modules, that aren't available in the doxhell environment,
    would fail. We patch the import machinery to selectively return a mock object for
    these. We make an exception for importing doxhell itself, since we still need the
    decorators to be available.
    """
    # Convert the path to a Python module name by removing the file extension and using
    # dots as separators (e.g. "tests/test_doxhell.py" -> "tests.test_doxhell")
    parts = file_path.parts[:-1] + (file_path.stem,)
    module_name = ".".join(parts)
    # Set up importing the source file directly. Based on:
    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    assert spec, f"Failed to create module spec for {file_path}"
    assert spec.loader, f"Spec for {file_path} has no loader"
    module = importlib.util.module_from_spec(spec)

    # Define a mock function for selectively importing modules. It allows any doxhell
    # related modules to be imported as normal, but returns a mock object for all other
    # modules.
    def selective_import(name, *args, **kwargs):
        if name.split(".")[0] == "doxhell":
            return builtin_import(name, *args, **kwargs)
        return unittest.mock.MagicMock()

    builtin_import = __import__
    # Patch the builtin import function during loading, to use our mock from above
    with unittest.mock.patch("builtins.__import__", side_effect=selective_import):
        spec.loader.exec_module(module)
    return module
