import sys
from typing import Tuple

import click
from loguru import logger

import doxhell.loaders
import doxhell.outputs
import doxhell.reviewers


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


@click.group()
def cli():
    """Command line interface entry point."""


@cli.command()
@click.option(
    "-v",
    "--verbose",
    "verbosity",
    default=0,
    count=True,
    help="Increase verbosity of logging output. Can be used multiple times, e.g. -vv.",
)
@click.option(
    "-t",
    "--test-dir",
    "test_dirs",
    default=(".",),
    multiple=True,
    help="The directory containing the automated tests.",
)
@click.option(
    "-d",
    "--docs-dir",
    "docs_dirs",
    default=(".",),
    multiple=True,
    help="The directory containing the documentation files.",
)
def review(
    verbosity: int, test_dirs: Tuple[str, ...], docs_dirs: Tuple[str, ...]
) -> None:
    """Validate requirements and tests; check coverage."""
    _setup_logging(verbosity)
    # Load all requirements and tests and convert to lists since we need to iterate
    # over them multiple times
    requirements = list(doxhell.loaders.load_requirements(docs_dirs[0]))
    manual_tests = list(doxhell.loaders.load_manual_tests(docs_dirs[0]))
    automated_tests = list(doxhell.loaders.load_automated_tests(test_dirs[0]))
    all_tests = automated_tests + manual_tests

    doxhell.reviewers.map_coverage(requirements, all_tests)
    problems = doxhell.reviewers.check_coverage(
        requirements
    ) + doxhell.reviewers.check_undefined_requirements(all_tests)

    doxhell.outputs.print_coverage_summary(requirements)
    doxhell.outputs.print_problems(problems)
    # If there were any problems, return a non-zero exit code
    sys.exit(len(problems))


if __name__ == "__main__":
    cli()
    # Run the main function with command line args and exit with the returned exit code
    # sys.exit(main(_parse_args()))
