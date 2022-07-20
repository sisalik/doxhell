from pathlib import Path

import click


class PathlibPath(click.Path):
    """A Click path argument that returns a pathlib.Path, not a string.

    Based on solution by jeremyh at
    https://github.com/pallets/click/issues/405#issuecomment-470812067
    """

    def convert(self, value, param, ctx):
        """Convert a string to a pathlib.Path."""
        return Path(super().convert(value, param, ctx))


def get_package_path() -> Path:
    """Get the path to the doxhell package - even when installed as a wheel."""
    return Path(__file__).parent.resolve()
