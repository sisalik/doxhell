import sys
from pathlib import Path
from typing import Dict, Tuple

import click
from loguru import logger

import doxhell.console
import doxhell.loaders
import doxhell.renderer
import doxhell.reviewer
from doxhell.renderer import OutputFormat


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
                    ("--test-dir", "test_dirs"),
                    default=(".",),
                    type=click.Path(exists=True, file_okay=False, dir_okay=True),
                    multiple=True,
                    help="The directory containing the automated tests. Can be passed "
                    "multiple times to analyse more than one directory.",
                ),
                click.Option(
                    ("--docs-dir", "docs_dirs"),
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
    """Automate software V&V documentation work."""


@cli.command(cls=StandardCommand)
def review(
    verbosity: int, test_dirs: Tuple[str, ...], docs_dirs: Tuple[str, ...]
) -> None:
    """Validate requirements and tests; check coverage."""
    _setup_logging(verbosity)
    requirements, _, problems = doxhell.reviewer.review(test_dirs, docs_dirs)
    doxhell.console.print_coverage_summary(requirements)
    doxhell.console.print_problems(problems)
    if problems:
        doxhell.console.print_result_bad("Review failed 😢")
    else:
        doxhell.console.print_result_good("✨ Your documentation is perfect! ✨")
    sys.exit(len(problems))


@cli.command(cls=StandardCommand)
@click.argument("target", type=click.Choice(["requirements", "coverage", "protocol"]))
@click.option(
    "-t",
    "--format",
    "formats",
    default=(OutputFormat.PDF,),
    type=click.Choice(list(OutputFormat)),
    multiple=True,
    help="The format to render the output in. Defaults to PDF. Can be passed multiple "
    "times to render in multiple formats.",
)
@click.option(
    "-o",
    "--output",
    "output_files",
    type=click.Path(),
    multiple=True,
    help="The output file path. Defaults to <target>.<format> (e.g. 'protocol.pdf'). "
    "Can also be passed multiple times, matching each --format option.",
)
@click.option(
    "-f",
    "--force",
    "force_overwrite",
    is_flag=True,
    help="Force overwriting of output files.",
)
def render(
    target: str,
    formats: Tuple[OutputFormat, ...],
    output_files: Tuple[str, ...],
    force_overwrite: bool,
    verbosity: int,
    test_dirs: Tuple[str, ...],
    docs_dirs: Tuple[str, ...],
) -> None:
    """Produce PDF output documents from source files."""
    if target in ("requirements", "coverage"):
        raise NotImplementedError(f"Rendering {target} is not yet implemented")
    output_map = _map_output_formats(target, formats, output_files, force_overwrite)

    _setup_logging(verbosity)
    _, tests, problems = doxhell.reviewer.review(test_dirs, docs_dirs)
    if problems:
        doxhell.console.print_problems(problems)
        doxhell.console.print_result_bad("Documentation is invalid; can't continue 😢")
        sys.exit(1)

    if target == "protocol":
        doxhell.renderer.render_protocol(tests, output_map)
        doxhell.console.print_result_good(f"Wrote {', '.join(output_map.values())}")


def _main():
    """Main entry point."""
    # Use loguru to catch errors in the CLI and print a nice traceback.
    with logger.catch():
        cli()


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


def _map_output_formats(
    target: str,
    formats: Tuple[OutputFormat, ...],
    output_files: Tuple[str, ...],
    force_overwrite: bool,
) -> Dict[OutputFormat, str]:
    """Validate and map output formats to output files."""
    # If no output files are specified, use the default output file paths.
    if not output_files:
        output_files = tuple(f"{target}.{format}" for format in formats)
    # Check for mismatched number of formats and output files.
    elif len(formats) != len(output_files):
        raise ValueError(
            f"Mismatched number of formats and output files: {len(formats)} formats "
            f"and {len(output_files)} output files"
        )
    # Check if any output files already exist.
    if not force_overwrite:
        for output_file in output_files:
            path = Path(output_file)
            if path.exists() and path.is_file():
                click.confirm(
                    f"File {output_file} already exists. Overwrite?", abort=True
                )
    return {format: output_file for format, output_file in zip(formats, output_files)}


if __name__ == "__main__":
    _main()
