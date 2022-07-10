import sys
from typing import Iterable

import rich
import rich.table

from doxhell.loaders import Requirement
from doxhell.reviewer import Problem, Severity


def print_coverage_summary(requirements: Iterable[Requirement]) -> None:
    """Print a summary of the requirements coverage."""
    table = rich.table.Table(title="Coverage summary", title_justify="left")
    table.add_column("Requirement", justify="right")
    table.add_column("Tests")
    table.add_column("Type")
    for requirement in requirements:
        if requirement.tests:
            colour_str = "[green]"
            tests_str = colour_str + "\n".join(test.id for test in requirement.tests)
            type_str = "\n".join(
                "[cyan]Auto" if test.automated else "[magenta]Manual"
                for test in requirement.tests
            )
        else:
            colour_str = "[red]"
            tests_str = colour_str + "NO TESTS"
            type_str = "[red]-"
        table.add_row(colour_str + requirement.id, tests_str, type_str)

    print()
    rich.print(table)


def print_problems(problems: Iterable[Problem]) -> None:
    """Print a colour-coded list of problems."""
    if not problems:
        return

    table = rich.table.Table(title="Problems", title_justify="left")
    table.add_column("Severity", justify="right")
    table.add_column("Description")
    # Map problem severity to colour
    row_styles = {
        Severity.HIGH: "white on red",
        Severity.MEDIUM: "red",
        Severity.LOW: "yellow",
    }
    for problem in problems:
        table.add_row(
            problem.severity,
            problem.description,
            style=row_styles[problem.severity],
        )
    print()
    rich.print(table)


def print_result_bad(message: str) -> None:
    """Print an error message to stderr."""
    rich.print(f"\n[red]{message}[/red]", file=sys.stderr)


def print_result_good(message: str) -> None:
    """Print a success message to stdout."""
    rich.print(f"\n[green]{message}[/green]")
