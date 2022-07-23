from pathlib import Path

import click.testing
import pytest

import doxhell.__main__
from doxhell.renderer import OutputType

SIMPLE_EXAMPLE_DIR = Path("examples") / "simple-project"
ADVANCED_EXAMPLE_DIR = Path("examples") / "advanced-project"


def test_smoke(cli_runner):
    """Test if the tool can run at all."""
    result = cli_runner.invoke(doxhell.__main__.cli)
    assert result.exit_code == 0


# Parametrize the project directory
@pytest.mark.usefixtures("_use_directory")
@pytest.mark.parametrize(
    "_use_directory",
    [SIMPLE_EXAMPLE_DIR, ADVANCED_EXAMPLE_DIR],
    indirect=True,
)
def test_example_project_review(cli_runner):
    """Test if the tool can review the example projects."""
    result = cli_runner.invoke(doxhell.__main__.cli, ["review"])
    assert result.exit_code == 0


# Parametrize the project directory and output type
@pytest.mark.usefixtures("_use_directory")
@pytest.mark.parametrize(
    ("_use_directory", "output_type"),
    [
        (SIMPLE_EXAMPLE_DIR, OutputType.REQUIREMENTS),
        (ADVANCED_EXAMPLE_DIR, OutputType.REQUIREMENTS),
        (ADVANCED_EXAMPLE_DIR, OutputType.PROTOCOL),
    ],
    indirect=["_use_directory"],
)
def test_example_project_render(cli_runner, temporary_file, output_type):
    """Test if the tool can render the output docs for the example projects."""
    result = cli_runner.invoke(
        doxhell.__main__.cli,
        ["render", output_type, "--output", temporary_file, "--force"],
    )
    assert result.exit_code == 0
    assert temporary_file.exists()


@pytest.fixture()
def cli_runner():
    """Fixture for a Click CLI runner."""
    return click.testing.CliRunner()
