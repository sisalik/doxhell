import difflib
import sys
from pathlib import Path
from typing import Iterator, List, Tuple

import click
import cssbeautifier  # type: ignore  # Skip type checking this module, no library stubs


@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True))
@click.option("--check", is_flag=True, default=False, help="Check only, don't fix")
def cli(path: Path | str, check: bool) -> None:
    """Auto-format CSS files using js-beautify."""
    path = Path(path)
    if path.is_dir():
        results = list(_format_dir(path, check))
    else:
        results = [(path, _format_file(path, check))]

    if check:
        for file, diff in results:
            if not diff:
                click.secho(f"{file} is valid", fg="green")
            else:
                click.secho(f"{file} is invalid", fg="red")
                _print_diff(diff)

        problems = sum(bool(diff) for _, diff in results)
        sys.exit(problems)
    # If auto-formatting, print a list of files that were fixed
    else:
        for file, diff in results:
            if diff:
                click.secho(f"{file} was fixed", fg="yellow")
            else:
                click.secho(f"{file} is already valid", fg="green")
        sys.exit(0)


def _format_dir(dir_path: Path, check: bool) -> Iterator[Tuple[Path, List[str]]]:
    for file in dir_path.glob("**/*.css"):
        yield file, _format_file(file, check)


def _format_file(file_path: Path, check: bool) -> List[str]:
    with open(file_path, "r") as file:
        original = file.read()
    formatted = cssbeautifier.beautify(original)
    # Only check, don't fix
    diff = list(
        difflib.unified_diff(
            original.splitlines(),
            formatted.splitlines(),
            "Original",
            "Formatted",
        ),
    )
    if not check:
        with open(file_path, "w") as file:
            file.write(formatted)
    return diff


def _print_diff(diff: List[str]) -> None:
    print()
    for line in diff:
        if line.startswith("+"):
            click.secho(line, fg="green")
        elif line.startswith("-"):
            click.secho(line, fg="red")
        elif line.startswith("@@"):
            click.secho(line, fg="cyan")
        else:
            print(line)


if __name__ == "__main__":
    cli()
