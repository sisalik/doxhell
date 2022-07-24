import importlib
import sys
import unittest.mock
from pathlib import Path
from types import ModuleType
from typing import Any, Hashable

from loguru import logger


def get_package_path() -> Path:
    """Get the path to the doxhell package - even when installed as a wheel."""
    return Path(__file__).parent.resolve()


def nested_get(dictionary: dict, *keys: Hashable) -> Any | None:
    """Get a value from a nested dictionary."""
    if len(keys) == 1:
        return dictionary.get(keys[0])
    return nested_get(dictionary[keys[0]], *keys[1:])


def setup_logging(verbosity: int) -> None:
    """Set up logging based on the verbosity level."""
    logger.remove()
    verbosity_to_level = {
        0: "WARNING",  # No -v argument
        1: "INFO",  # -v
        2: "DEBUG",  # -vv
    }
    try:
        logger.add(sys.stderr, level=verbosity_to_level[verbosity])
    except KeyError:
        raise ValueError(f"Invalid verbosity level: {verbosity}")


def import_module(file_path: Path) -> ModuleType:
    """Import the given module, without having the module dependencies installed.

    We need to be able to import test modules without having the project dependencies
    installed. This is because doxhell may be installed in an environment outside of the
    project.

    Normally, imports of any modules, that aren't available in the doxhell environment,
    would fail. We patch the import machinery to selectively return a mock object for
    these. Any imports that succeed will be returned as normal.
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
    builtin_import = __import__

    # Define a mock function for selectively importing modules. It allows any installed
    # modules to be imported as normal, but returns a mock object for all other modules.
    def selective_import(name, *args, **kwargs):
        try:
            return builtin_import(name, *args, **kwargs)
        except ImportError:
            return unittest.mock.MagicMock()

    # Patch the builtin import function during loading, to use our mock from above
    with unittest.mock.patch("builtins.__import__", side_effect=selective_import):
        spec.loader.exec_module(module)
    return module
