import sys
from pathlib import Path
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
