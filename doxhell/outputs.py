from typing import Iterable

import rich.console
import rich.table

from doxhell.loaders import Requirement


def print_coverage_summary(requirements: Iterable[Requirement]) -> None:
    table = rich.table.Table(title="Coverage summary")
    table.add_column("Requirement")
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

    console = rich.console.Console()
    console.print(table)
