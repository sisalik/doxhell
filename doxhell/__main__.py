import sys
from typing import Tuple

import click
from loguru import logger

import doxhell.console
import doxhell.loaders
import doxhell.renderer
import doxhell.reviewer


class StandardCommand(click.Command):
    """CLI command with common options."""

    def __init__(self, *args, **kwargs):
        """Initialise a StandardCommand instance."""
        super().__init__(*args, **kwargs)
        self.params.extend(
            [
                click.Option(
                    ("-v", "--verbose", "verbosity"),
                    default=0,
                    type=click.IntRange(0, 2),
                    count=True,
                    help="Increase verbosity of logging output. Can be used multiple "
                    "times, e.g. -vv.",
                ),
                click.Option(
                    ("-t", "--test-dir", "test_dirs"),
                    default=(".",),
                    type=click.Path(exists=True, file_okay=False, dir_okay=True),
                    multiple=True,
                    help="The directory containing the automated tests. Can be passed "
                    "multiple times to analyse more than one directory.",
                ),
                click.Option(
                    ("-d", "--docs-dir", "docs_dirs"),
                    default=(".",),
                    type=click.Path(exists=True, file_okay=False, dir_okay=True),
                    multiple=True,
                    help="The directory containing the documentation files. Can be "
                    "passed multiple times to analyse more than one directory.",
                ),
            ]
        )


@click.group()
def cli():
    """Command line interface entry point."""


@cli.command(cls=StandardCommand)
def review(
    verbosity: int, test_dirs: Tuple[str, ...], docs_dirs: Tuple[str, ...]
) -> None:
    """Validate requirements and tests; check coverage."""
    _setup_logging(verbosity)
    requirements, _, problems = doxhell.reviewer.review(test_dirs, docs_dirs)
    doxhell.console.print_coverage_summary(requirements)
    print()
    doxhell.console.print_problems(problems)
    if problems:
        doxhell.console.print_result_bad("Review failed 😢")
    else:
        doxhell.console.print_result_good("✨ Your documentation is perfect! ✨")
    sys.exit(len(problems))


@cli.command(cls=StandardCommand)
@click.argument("target", type=click.Choice(["requirements", "coverage", "protocol"]))
def render(
    target: str, verbosity: int, test_dirs: Tuple[str, ...], docs_dirs: Tuple[str, ...]
) -> None:
    """Produce PDF output documents from source files."""
    if target in ("requirements", "coverage"):
        raise NotImplementedError(f"Rendering {target} is not yet implemented")
    _setup_logging(verbosity)
    _, tests, problems = doxhell.reviewer.review(test_dirs, docs_dirs)
    if problems:
        doxhell.console.print_problems(problems)
        doxhell.console.print_result_bad("Documentation is invalid; can't continue 😢")
        sys.exit(1)

    if target == "protocol":
        pdf_filename = doxhell.renderer.render_protocol(tests)
        doxhell.console.print_result_good(f"Wrote {pdf_filename}")


def _setup_logging(verbosity: int) -> None:
    logger.remove()
    if verbosity == 0:
        logger.add(sys.stderr, level="WARNING")
    elif verbosity == 1:
        logger.add(sys.stderr, level="INFO")
    elif verbosity == 2:
        logger.add(sys.stderr, level="DEBUG")
    else:
        raise ValueError(f"Invalid verbosity level: {verbosity}")


if __name__ == "__main__":
    with logger.catch():
        cli()
