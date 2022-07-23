from collections.abc import Iterable

import rich
import rich.console
import rich.table

from doxhell.models import CoverageCollection
from doxhell.reviewer import Problem


def print_coverage_summary(coverage: CoverageCollection) -> None:
    """Print a summary of the requirements coverage."""
    table = rich.table.Table(title="Coverage summary", title_justify="left")
    table.add_column("Requirement", justify="right")
    table.add_column("Tests")
    table.add_column("Type")
    for requirement, tests in coverage.mapping.items():
        # TODO: This is a bit of a hack, but it works for now
        if tests:
            colour_str = "[green]"
            tests_str = colour_str + "\n".join(test.full_name for test in tests)
            type_str = "\n".join(
                "[cyan]Auto" if test.automated else "[magenta]Manual" for test in tests
            )
        elif requirement.obsolete:
            tests_str = "[gray]NO TESTS (OBSOLETE)"
            type_str = "[gray]-"
        else:
            colour_str = "[red]"
            tests_str = f"{colour_str}NO TESTS"
            type_str = "[red]-"
        # For obsolete requirements, override all styles
        if requirement.obsolete:
            colour_str = "[gray][strike]"
            tests_str = f"{colour_str}{tests_str.split(']')[1]}"
            type_str = f"{colour_str}{type_str.split(']')[1]}"
        table.add_row(f"{colour_str}{requirement.id}", tests_str, type_str)

    print()
    rich.print(table)


def print_problems(problems: Iterable[Problem]) -> None:
    """Print a colour-coded list of problems."""
    if not problems:
        return

    table = rich.table.Table(title="Problems", title_justify="left")
    table.add_column("Code")
    table.add_column("Description")
    for problem in sorted(problems, key=lambda p: p.code):
        table.add_row(
            problem.code.name,
            problem.description,
            style=_problem_code_to_colour(problem.code.value),
        )
    print()
    rich.print(table)


def print_result_bad(message: str) -> None:
    """Print an error message to stderr."""
    rich.console.Console(highlight=False).print(f"\n{message}", style="red")


def print_result_good(message: str) -> None:
    """Print a success message to stdout."""
    rich.console.Console(highlight=False).print(f"\n{message}", style="green")


def _problem_code_to_colour(problem_code: int) -> str:
    """Return a Rich colour string for a given problem code."""
    # Use standard colours from 1 to 15, since 0 is black
    colour_idx = (problem_code - 1) % 15 + 1
    return f"color({colour_idx})"
