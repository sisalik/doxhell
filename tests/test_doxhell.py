import contextlib
import os
from pathlib import Path

import click.testing
import pytest

import doxhell.__main__


def test_smoke(cli_runner):
    """Test if the tool can run at all."""
    result = cli_runner.invoke(doxhell.__main__.cli)
    assert result.exit_code == 0


def test_example_project_review(cli_runner):
    """Test if the tool can review an example project."""
    with set_directory(Path("examples") / "example-project"):
        result = cli_runner.invoke(doxhell.__main__.cli, ["review"])
    assert result.exit_code == 0


def test_example_project_render_protocol(cli_runner):
    """Test if the tool can render the test protocol for an example project."""
    temp_pdf_file = Path("test_example_project_render_protocol.pdf").resolve()
    with set_directory(Path("examples") / "example-project"):
        result = cli_runner.invoke(
            doxhell.__main__.cli, ["render", "protocol", "-o", str(temp_pdf_file)]
        )
        assert result.exit_code == 0
        assert temp_pdf_file.exists()
    temp_pdf_file.unlink(missing_ok=True)


@pytest.fixture()
def cli_runner():
    """Fixture for a Click CLI runner."""
    return click.testing.CliRunner()


@contextlib.contextmanager
def set_directory(directory: Path | str):
    """Context manager for (temporarily) changing the current working directory."""
    original_directory = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(original_directory)
