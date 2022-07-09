import argparse
import sys

from loguru import logger

import doxhell.loaders
import doxhell.outputs
import doxhell.reviewers


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Doxhell")
    parser.add_argument(
        "--docs-dir",
        default=".",
        help="The directory containing the Doxhell documentation. Defaults to the "
        "current directory.",
    )
    parser.add_argument(
        "--test-dir",
        default=".",
        help="The directory containing the automated tests. Defaults to the current "
        "directory.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity of logging output.",
    )
    return parser.parse_args()


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


def main() -> int:
    args = _parse_args()
    _setup_logging(args.verbose)
    # Load all requirements and tests and convert to lists since we need to iterate
    # over them multiple times
    requirements = list(doxhell.loaders.load_requirements(args.docs_dir))
    manual_tests = list(doxhell.loaders.load_manual_tests(args.docs_dir))
    automated_tests = list(doxhell.loaders.load_automated_tests(args.test_dir))
    all_tests = automated_tests + manual_tests

    doxhell.reviewers.map_coverage(requirements, all_tests)
    coverage_problems = doxhell.reviewers.check_coverage(requirements)
    undefined_problems = doxhell.reviewers.check_undefined_requirements(all_tests)

    doxhell.outputs.print_coverage_summary(requirements)
    # If there are any problems, return a non-zero exit code
    return len(coverage_problems) + len(undefined_problems)


if __name__ == "__main__":
    sys.exit(main())
