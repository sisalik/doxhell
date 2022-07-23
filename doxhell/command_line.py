from pathlib import Path
from typing import Any, Iterable

import click
import toml
from click.core import ParameterSource
from loguru import logger

import doxhell.utils
from doxhell.reviewer import ProblemCode

# The name of the default config file that is used if no config file is specified.
# If this does not exist, only command line arguments will be used.
DEFAULT_CONFIG_FILE = "pyproject.toml"
# Tuple of nested keys in the config structure, where doxhell settings are stored.
# Example: ("tool", "doxhell") corresponds to config["tool"]["doxhell"].
CONFIG_FILE_KEY = ("tool", "doxhell")


class PathlibPath(click.Path):
    """A Click parameter type that converts into a pathlib.Path.

    Based on solution by jeremyh at
    https://github.com/pallets/click/issues/405#issuecomment-470812067
    """

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> Path:
        """Convert a string to a pathlib.Path."""
        return Path(super().convert(value, param, ctx))


class ProblemCodeType(click.ParamType):
    """A Click parameter type for problem codes."""

    name = "problem_code"

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> ProblemCode:
        """Convert a string to a problem code."""
        try:
            return ProblemCode[value]
        except KeyError:
            self.fail(f"{value} is not a valid problem code", param, ctx)


class BaseCommand(click.Command):
    """CLI command class with common options."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialise a BaseCommand instance and define common options."""
        super().__init__(*args, **kwargs)
        self.params.extend(
            [
                # Note: the verbosity option is not passed to the command callback
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
                    type=PathlibPath(exists=True, file_okay=False, dir_okay=True),
                    multiple=True,
                    help="The directory containing the automated tests. Can be passed "
                    "multiple times to analyse more than one directory.",
                ),
                click.Option(
                    ("--docs-dir", "docs_dirs"),
                    default=(".",),
                    type=PathlibPath(exists=True, file_okay=False, dir_okay=True),
                    multiple=True,
                    help="The directory containing the documentation files. Can be "
                    "passed multiple times to analyse more than one directory.",
                ),
                click.Option(
                    ("-i", "--ignore", "ignores"),
                    type=ProblemCodeType(),
                    multiple=True,
                    help="The problem codes to ignore. Can be passed multiple times to "
                    "ignore more than one problem.",
                ),
                # Note: the config_file option is not passed to the command callback
                click.Option(
                    ("-c", "--config-file", "config_file"),
                    type=PathlibPath(exists=True, file_okay=True, dir_okay=False),
                    help="The path to the config file to load. pyproject.toml is tried "
                    "by default. Arguments passed via command line take precedence "
                    "over those in the config file.",
                ),
            ]
        )

    def invoke(self, ctx: click.Context) -> Any:
        """Load parameters from a config file, if available, and invoke the command.

        Decision logic:
            1. If a config file is specified, load it. Existence is verified by Click.
            2. If a config file is not specified, try loading pyproject.toml.
            3. If neither of the above is found, use only command line arguments.
            4. If command line arguments are not specified, use the default values.
        """
        # Every run of the application needs logging set up
        doxhell.utils.setup_logging(ctx.params["verbosity"])

        config_file: Path = ctx.params["config_file"] or Path(DEFAULT_CONFIG_FILE)
        if config_file.exists():
            logger.info(f"Loading config file: {config_file}")
            self._apply_config_from_file(config_file, ctx)
        # Don't pass verbosity and config_file to the command, as they are already
        # handled before invocation
        for key in ("verbosity", "config_file"):
            ctx.params.pop(key)
        return super().invoke(ctx)

    def _apply_config_from_file(self, config_file: Path, ctx: click.Context) -> None:
        """Load and apply parameters from a config file."""
        if not (config := self._load_config_from_file(config_file, ctx)):
            return
        # Find a matching config member for each parameter
        for param_name in ctx.params:
            # Only override parameters not already supplied via other means
            if (
                ctx.get_parameter_source(param_name) is ParameterSource.DEFAULT
                and param_name in config
            ):
                logger.debug(f"Overriding {param_name} -> {config[param_name]}")
                value = self._convert_parameter(config[param_name], param_name, ctx)
                ctx.params[param_name] = value
                # If verbosity is set, we need to re-setup logging with the new level
                if param_name == "verbosity":
                    doxhell.utils.setup_logging(value)

    def _load_config_from_file(
        self, config_file: Path, ctx: click.Context
    ) -> dict | None:
        """Load the config file and return a dictionary of the doxhell section."""
        try:
            config = toml.load(config_file)
        except toml.TomlDecodeError as e:
            raise click.ClickException(f"Could not load config file {config_file}: {e}")

        doxhell_config = doxhell.utils.nested_get(config, *CONFIG_FILE_KEY)
        if not doxhell_config:
            logger.info(
                "Config file does not contain a doxhell section. Using command line "
                "arguments only."
            )
            return None
        # Check for any unrecognised parameters
        for param_name in doxhell_config:
            if param_name not in ctx.params:
                raise click.UsageError(
                    f"Unrecognised parameter '{param_name}' in config file", ctx
                )
        return doxhell_config

    def _convert_parameter(
        self, value: Any, param_name: str, ctx: click.Context
    ) -> Any:
        """Convert a parameter using the defined converter.

        We need to do this manually because Click converts parameters during
        initialisation but we are overriding parameters later, during invocation.
        """
        # Find the parameter type that matches the parameter name
        for param in self.params:
            if param.name == param_name:
                break
        else:
            # This should never happen
            raise ValueError(f"Could not find type for parameter {param_name}")

        if param.multiple:
            # For parameters expecting a list of values, accept a comma-separated
            # string
            if isinstance(value, str):
                value = (v.strip() for v in value.split(","))
            elif not isinstance(value, Iterable):
                raise click.UsageError(
                    f"Invalid value for '{param_name}': {value} (expected a list of "
                    f"'{param.type.name}' or comma-separated string)",
                    ctx,
                )
            return [param.type.convert(v, param, ctx) for v in value]
        # For a single value parameter, the value should not be iterable
        if isinstance(value, Iterable):
            raise click.UsageError(
                f"Invalid value for '{param_name}': {value} (expected a single "
                f"'{param.type.name}')",
                ctx,
            )
        return param.type.convert(value, param, ctx)
