import contextlib
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator

import click.testing
import pytest

import doxhell.__main__
from doxhell.renderer import OutputType


def test_smoke(cli_runner):
    """Test if the tool can run at all."""
    result = cli_runner.invoke(doxhell.__main__.cli)
    assert result.exit_code == 0


def test_example_project_review(cli_runner):
    """Test if the tool can review an example project."""
    with set_directory(Path("examples") / "example-project"):
        result = cli_runner.invoke(doxhell.__main__.cli, ["review"])
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "output_type",
    [
        OutputType.REQUIREMENTS,
        OutputType.PROTOCOL,
    ],
)
def test_example_project_render(cli_runner, output_type):
    """Test if the tool can render the output docs for an example project."""
    with temporary_file(suffix=".pdf") as output_file:
        with set_directory(Path("examples") / "example-project"):
            result = cli_runner.invoke(
                doxhell.__main__.cli,
                ["render", output_type, "--output", output_file, "--force"],
            )
            assert result.exit_code == 0
            assert output_file.exists()


@pytest.fixture()
def cli_runner():
    """Fixture for a Click CLI runner."""
    return click.testing.CliRunner()


@contextlib.contextmanager
def set_directory(directory: Path | str):
    """Context manager for (temporarily) changing the current working directory."""
    original_directory = os.getcwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(original_directory)


@contextlib.contextmanager
def temporary_file(**kwargs: Any) -> Iterator[Path]:
    """Context manager for creating a temporary file."""
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, **kwargs)
        temp_file.close()
        temp_file_path = Path(temp_file.name)
        yield temp_file_path
    finally:
        temp_file_path.unlink()
