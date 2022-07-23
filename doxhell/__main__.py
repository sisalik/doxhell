import sys
from pathlib import Path

import click
from loguru import logger

import doxhell.console
import doxhell.loaders
import doxhell.renderer
import doxhell.reviewer
import doxhell.utils
from doxhell.command_line import BaseCommand, PathlibPath
from doxhell.renderer import OutputFormat, OutputType
from doxhell.reviewer import ProblemCode


@click.group()
def cli():
    """Automate software V&V documentation work."""


@cli.command(cls=BaseCommand)
def review(
    test_dirs: tuple[Path, ...],
    docs_dirs: tuple[Path, ...],
    ignores: tuple[ProblemCode, ...],
) -> None:
    """Validate requirements and tests; check coverage."""
    requirements, _, problems = doxhell.reviewer.review(test_dirs, docs_dirs, ignores)
    doxhell.console.print_coverage_summary(requirements)
    if problems:
        doxhell.console.print_problems(problems)
        doxhell.console.print_result_bad("Review failed 😢")
    else:
        doxhell.console.print_result_good("✨ Your documentation is perfect! ✨")
    sys.exit(len(problems))


@cli.command(cls=BaseCommand)
@click.argument("target", type=click.Choice(list(OutputType)))
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
    type=PathlibPath(),
    multiple=True,
    help="The output file path. Defaults to <title>.<format> (e.g. "
    "'Title-Loaded-From-YAML.pdf'). Can also be passed multiple times, matching each "
    "--format option.",
)
@click.option(
    "-f",
    "--force",
    "force_overwrite",
    is_flag=True,
    help="Force overwriting of output files.",
)
def render(
    target: OutputType,
    formats: tuple[OutputFormat, ...],
    output_files: tuple[str, ...],
    force_overwrite: bool,
    test_dirs: tuple[Path, ...],
    docs_dirs: tuple[Path, ...],
    ignores: tuple[ProblemCode, ...],
) -> None:
    """Produce PDF output documents from source files."""
    if target not in [OutputType.REQUIREMENTS, OutputType.PROTOCOL]:
        raise NotImplementedError(f"Rendering {target} is not yet implemented")
    # Check for mismatched number of formats and output files
    if len(output_files) > 0 and len(output_files) != len(formats):
        raise click.UsageError(
            f"Mismatched number of formats ({len(formats)}) and output files "
            f"({len(output_files)})"
        )
    # Check if documentation is valid before rendering
    requirements, tests, problems = doxhell.reviewer.review(
        test_dirs, docs_dirs, ignores
    )
    if problems:
        doxhell.console.print_problems(problems)
        doxhell.console.print_result_bad("Documentation is invalid; can't continue 😢")
        sys.exit(len(problems))
    # Select the document object depending on the rendering target
    document = {
        OutputType.REQUIREMENTS: requirements,
        OutputType.PROTOCOL: tests.manual_tests_doc,
    }[target]
    # It's possible to have a valid documentation set without any manual tests, but this
    # means you can't render the protocol
    if not document:
        doxhell.console.print_result_bad(f"No source file for {target} document exists")
        sys.exit(1)
    # Compile metadata as context to be included in the rendered documents. Used in
    # Jinja templates.
    # TODO: Load extra context from config file/CLI options/package metadata etc.
    context = {"document": document}
    output_map = _map_output_formats(formats, output_files, document, force_overwrite)
    doxhell.renderer.render(target, output_map, context)
    output_files_str = ", ".join(str(f) for f in output_map.values())
    doxhell.console.print_result_good(f"Wrote {output_files_str}")


def _main():
    """Main entry point."""
    # Use loguru to catch errors in the CLI and print a nice traceback
    with logger.catch():
        cli()


def _map_output_formats(
    formats: tuple[OutputFormat, ...],
    output_files: tuple[str, ...],
    document: doxhell.loaders.RequirementsDoc | doxhell.loaders.TestsDoc,
    force_overwrite: bool,
) -> dict[OutputFormat, str]:
    """Validate and map output formats to output files."""
    # If no output files are specified, use the document title as the file name
    if not output_files:
        output_files = tuple(f"{document.title}.{format}" for format in formats)
    # Check if any output files already exist
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
