from collections.abc import Iterable

import rich
import rich.console
import rich.table

from doxhell.loaders import RequirementsDoc
from doxhell.reviewer import Problem


def print_coverage_summary(requirements_spec: RequirementsDoc) -> None:
    """Print a summary of the requirements coverage."""
    table = rich.table.Table(title="Coverage summary", title_justify="left")
    table.add_column("Requirement", justify="right")
    table.add_column("Tests")
    table.add_column("Type")
    for requirement in requirements_spec.requirements:
        if requirement.tests:
            colour_str = "[green]"
            tests_str = colour_str + "\n".join(
                test.full_name for test in requirement.tests
            )
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
