from pathlib import Path


def get_package_path() -> Path:
    """Get the path to the doxhell package - even when installed as a wheel."""
    return Path(__file__).parent.resolve()
