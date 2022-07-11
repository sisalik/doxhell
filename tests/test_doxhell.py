import click.testing

import doxhell.__main__


def test_smoke():
    """Test if the tool can run at all."""
    runner = click.testing.CliRunner()
    result = runner.invoke(doxhell.__main__.cli)
    assert result.exit_code == 0
