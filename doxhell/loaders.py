import dataclasses
import enum
import importlib
import inspect
import unittest.mock
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Iterable, Iterator, List, Optional

import yaml
from loguru import logger


@dataclasses.dataclass
class Requirement:
    """A requirement found in the documentation."""

    id: str
    tests: List["Test"] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Test:
    """A test found in the documentation or automated test module."""

    id: str
    description: str
    requirement_ids: List[str]
    automated: bool
    requirements: List[Requirement] = dataclasses.field(default_factory=list)
    steps: List["TestStep"] = dataclasses.field(default_factory=list)


class EvidenceType(str, enum.Enum):
    """The type of evidence used to prove that a manual test passed."""

    SCREENSHOT = "screenshot"
    LOG = "log"
    OBSERVATION = "observation"
    SETTINGS = "settings"


@dataclasses.dataclass
class TestStep:
    """A step in a test."""

    given: str
    when: str
    then: str
    evidence: Optional[EvidenceType] = None


def load_requirements(docs_root_dirs: Iterable[Path | str]) -> Iterator[Requirement]:
    """Load all requirements from the given paths."""
    # Ignore duplicate directories
    for docs_root_dir in set(docs_root_dirs):
        yield from _load_requirements_single(docs_root_dir)


def load_tests(
    docs_root_dirs: Iterable[Path | str], test_root_dirs: Iterable[Path | str]
) -> Iterator[Test]:
    """Load all tests from the given paths."""
    # Ignore duplicate directories
    for docs_root_dir in set(docs_root_dirs):
        yield from _load_manual_tests_single(docs_root_dir)
    for test_root_dir in set(test_root_dirs):
        yield from _load_automated_tests_single(test_root_dir)


def _load_requirements_single(docs_root_dir: Path | str = ".") -> Iterator[Requirement]:
    """Load all requirements from the given path."""
    if isinstance(docs_root_dir, str):
        docs_root_dir = Path(docs_root_dir)
    logger.info("Looking for requirements in {}", docs_root_dir)

    for item in docs_root_dir.rglob("*.y*ml"):
        if item.stem == "requirements":
            logger.debug("Found requirements file: {}", item)
            with open(item) as file:
                yield from _load_requirements_from_yaml(file)


def _load_manual_tests_single(docs_root_dir: Path | str = ".") -> Iterator[Test]:
    """Load all manual tests from the given path."""
    if isinstance(docs_root_dir, str):
        docs_root_dir = Path(docs_root_dir)
    logger.info("Looking for manual tests in {}", docs_root_dir)

    for item in docs_root_dir.rglob("*.y*ml"):
        if item.stem == "tests":
            logger.debug("Found tests file: {}", item)
            with open(item) as file:
                yield from _load_tests_from_yaml(file)


def _load_automated_tests_single(test_root_dir: Path | str = ".") -> Iterator[Test]:
    """Load all automated tests from the given path."""
    logger.info("Looking for tests in {}", test_root_dir)
    test_files = _find_test_files(test_root_dir)
    for test_file in test_files:
        for test_function in _find_test_functions(test_file):
            if hasattr(test_function, "requirement_ids"):
                full_test_name = f"{test_file}::{test_function.__name__}"
                test = Test(
                    full_test_name,
                    str(test_function.__doc__),
                    # mypy doesn't think this function has a "requirement_ids" attribute
                    # but we clearly guard against that above
                    test_function.requirement_ids,  # type: ignore
                    True,
                )
                yield test


def _load_requirements_from_yaml(file) -> Iterator[Requirement]:
    """Load all requirements from the given YAML file."""
    # TODO: Use pydantic (?) to validate the YAML file
    for member in yaml.safe_load(file):
        yield Requirement(member["requirement"])


def _load_tests_from_yaml(file) -> Iterator[Test]:
    """Load all tests from the given YAML file."""
    # TODO: Use pydantic (?) to validate the YAML file
    for member in yaml.safe_load(file):
        full_test_name = f"{file.name}::{member['test']}"
        test = Test(full_test_name, member["description"], member["covers"], False)
        for step in member["steps"]:
            test_step = TestStep(
                step["given"],
                step["when"],
                step["then"],
                EvidenceType(step["evidence"]) if "evidence" in step else None,
            )
            test.steps.append(test_step)
        logger.debug(test)
        yield test


def _find_test_files(path: str | Path) -> Iterator[Path]:
    """Find all automated test files in the given path."""
    if isinstance(path, str):
        path = Path(path)

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


def _find_test_functions(file_path: Path) -> Iterator[FunctionType]:
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
