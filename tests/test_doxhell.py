import click.testing
import pytest

import doxhell.__main__
from doxhell.renderer import OutputType


def test_smoke(cli_runner):
    """Test if the tool can run at all."""
    result = cli_runner.invoke(doxhell.__main__.cli)
    assert result.exit_code == 0


@pytest.mark.usefixtures("_use_directory")
def test_example_project_review(cli_runner):
    """Test if the tool can review an example project."""
    result = cli_runner.invoke(doxhell.__main__.cli, ["review"])
    assert result.exit_code == 0


# Paramterize the output document type
@pytest.mark.parametrize(
    "output_type",
    [
        OutputType.REQUIREMENTS,
        OutputType.PROTOCOL,
    ],
)
@pytest.mark.usefixtures("_use_directory")
def test_example_project_render(cli_runner, temporary_file, output_type):
    """Test if the tool can render the output docs for an example project."""
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
