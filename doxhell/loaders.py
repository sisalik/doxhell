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

from doxhell.decorators import VerificationTest


class Requirement(BaseModel):
    """A requirement found in the documentation."""

    id: str
    specification: str
    rationale: str
    parent: str = ""
    obsolete: bool = False
    obsolete_reason: str = ""
    # List of tests populated during cross check with tests
    tests: list["Test"] = []

    @validator("obsolete_reason", always=True)
    def obsolete_reason_must_be_given(cls, v, values):
        """Validate that obsolete_reason is given if obsolete is True."""
        if values["obsolete"] and not v:
            raise ValueError("obsolete_reason is required if obsolete is True")
        return v


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
    # List of requirements populated during cross check with requirements
    requirements: list[Requirement] = []
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


class RequirementsDoc(BaseModel):
    """A requirements specification document."""

    title: str
    author: str
    file_path: Path
    requirements: list[Requirement]


class TestsDoc(BaseModel):
    """A manual test protocol document."""

    title: str
    author: str
    file_path: Path
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
    """Load all requirements from the given paths."""
    requirements_docs = list(_load_all_requirements_docs(docs_root_dirs))
    if not requirements_docs:
        raise ValueError(f"No requirements found in directories {docs_root_dirs}")
    elif len(requirements_docs) > 1:
        file_paths = "; ".join(str(r.file_path) for r in requirements_docs)
        raise ValueError(f"Multiple requirements found: {file_paths}")
    return requirements_docs[0]


def load_tests(
    docs_root_dirs: Iterable[Path], test_root_dirs: Iterable[Path]
) -> TestSuite:
    """Load all tests from the given paths."""
    manual_test_docs = list(_load_all_manual_test_docs(docs_root_dirs))
    if len(manual_test_docs) > 1:
        file_paths = "; ".join(str(r.file_path) for r in manual_test_docs)
        raise ValueError(f"Multiple manual test protocols found: {file_paths}")

    automated_tests = list(_load_all_automated_tests(test_root_dirs))
    return TestSuite(
        manual_tests_doc=manual_test_docs[0] if manual_test_docs else None,
        automated_tests=automated_tests,
    )


def _load_all_requirements_docs(
    docs_root_dirs: Iterable[Path],
) -> Iterator[RequirementsDoc]:
    """Load all requirements documents from the given paths."""
    for docs_root_dir in set(docs_root_dirs):  # Ignore duplicate directories
        logger.info("Looking for requirements in {}", docs_root_dir)
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
        return RequirementsDoc(file_path=file_path, **data)
    except ValidationError:
        logger.error("Error parsing requirements file: {}", file_path)
        raise


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
