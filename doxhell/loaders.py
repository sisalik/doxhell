import dataclasses
import importlib
import inspect
from pathlib import Path
from typing import Callable, Iterator, List

import yaml

from doxhell.decorators import TestFunction


@dataclasses.dataclass
class Requirement:
    id: str
    tests: List["Test"] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Test:
    id: str
    description: str
    requirement_ids: List[str]
    automated: bool
    requirements: List[Requirement] = dataclasses.field(default_factory=list)


def load_requirements(docs_root_dir: Path | str = ".") -> Iterator[Requirement]:
    """Load all requirements from the given path."""
    if isinstance(docs_root_dir, str):
        docs_root_dir = Path(docs_root_dir)

    for item in docs_root_dir.rglob("*.y*ml"):
        if item.stem == "requirements":
            with open(item) as file:
                yield from _load_requirements_from_yaml(file)


def load_manual_tests(docs_root_dir: Path | str = ".") -> Iterator[Test]:
    """Load all manual tests from the given path."""
    if isinstance(docs_root_dir, str):
        docs_root_dir = Path(docs_root_dir)

    for item in docs_root_dir.rglob("*.y*ml"):
        if item.stem == "tests":
            with open(item) as file:
                yield from _load_tests_from_yaml(file)


def load_automated_tests(test_root_dir: Path | str = ".") -> Iterator[Test]:
    test_files = _find_test_files(test_root_dir)
    for test_file in test_files:
        for test_function in _find_test_functions(test_file):
            if hasattr(test_function, "requirement_ids"):
                full_test_name = f"{test_file}::{test_function.__name__}"
                test = Test(
                    full_test_name,
                    str(test_function.__doc__),
                    test_function.requirement_ids,
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
        yield Test(full_test_name, member["description"], member["covers"], False)


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
            yield item


def _find_test_functions(file_path: Path) -> Iterator[TestFunction]:
    """Find all test functions in the given module."""
    # Convert the path to a module name by removing the file extension
    parts = file_path.parts[:-1] + (file_path.stem,)
    module = importlib.import_module(".".join(parts))
    for name, obj in inspect.getmembers(module):
        if name.startswith("test"):
            yield obj
