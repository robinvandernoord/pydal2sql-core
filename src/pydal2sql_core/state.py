import contextlib
import inspect
import operator
import os
import sys
import typing
from dataclasses import dataclass
from enum import Enum, EnumMeta
from pathlib import Path
from typing import Any, Optional

import configuraptor
import tomli
from configuraptor import alias, postpone
from configuraptor.helpers import find_pyproject_toml

from .types import (
    DEFAULT_OUTPUT_FORMAT,
    SUPPORTED_DATABASE_TYPES_WITH_ALIASES,
    SUPPORTED_OUTPUT_FORMATS,
)


class ReprEnumMeta(EnumMeta):
    """
    Give an Enum class a fancy repr.
    """

    def __repr__(cls) -> str:  # sourcery skip
        """
        Print all of the enum's members.
        """
        options = typing.cast(typing.Iterable[Enum], cls.__members__.values())  # for mypy
        members_repr = ", ".join(f"{m.value!r}" for m in options)
        return f"{cls.__name__}({members_repr})"


class DynamicEnum(Enum, metaclass=ReprEnumMeta):
    """
    Cmobine the enum class with the ReprEnumMeta metaclass.
    """


def create_enum_from_literal(name: str, literal_type: typing.Any) -> typing.Type[DynamicEnum]:
    """
    Transform a typing.Literal statement into an Enum.

    literal_type can be a typing.Literal or a Union of Literals
    """
    literals: list[str] = []

    if hasattr(literal_type, "__args__"):
        for arg in typing.get_args(literal_type):
            if hasattr(arg, "__args__"):
                # e.g. literal_type = typing.Union[typing.Literal['one', 'two']]
                literals.extend(typing.get_args(arg))
            else:
                # e.g. literal_type = typing.Literal['one', 'two']
                literals.append(arg)
    else:
        # e.g. literal_type = 'one'
        literals.append(str(literal_type))

    literals.sort()

    enum_dict = {}

    for literal in literals:
        enum_name = literal.replace(" ", "_").upper()
        enum_value = literal
        enum_dict[enum_name] = enum_value

    return DynamicEnum(name, enum_dict)  # type: ignore


class Verbosity(Enum):
    """
    Verbosity is used with the --verbose argument of the cli commands.
    """

    # typer enum can only be string
    quiet = "1"
    normal = "2"
    verbose = "3"
    debug = "4"  # only for internal use

    @staticmethod
    def _compare(
        self: "Verbosity",
        other: "Verbosity_Comparable",
        _operator: typing.Callable[["Verbosity_Comparable", "Verbosity_Comparable"], bool],
    ) -> bool:
        """
        Abstraction using 'operator' to have shared functionality between <, <=, ==, >=, >.

        This enum can be compared with integers, strings and other Verbosity instances.

        Args:
            self: the first Verbosity
            other: the second Verbosity (or other thing to compare)
            _operator: a callable operator (from 'operators') that takes two of the same types as input.
        """
        match other:
            case Verbosity():
                return _operator(self.value, other.value)
            case int():
                return _operator(int(self.value), other)
            case str():
                return _operator(int(self.value), int(other))

    def __gt__(self, other: "Verbosity_Comparable") -> bool:
        """
        Magic method for self > other.
        """
        return self._compare(self, other, operator.gt)

    def __ge__(self, other: "Verbosity_Comparable") -> bool:
        """
        Method magic for self >= other.
        """
        return self._compare(self, other, operator.ge)

    def __lt__(self, other: "Verbosity_Comparable") -> bool:
        """
        Magic method for self < other.
        """
        return self._compare(self, other, operator.lt)

    def __le__(self, other: "Verbosity_Comparable") -> bool:
        """
        Magic method for self <= other.
        """
        return self._compare(self, other, operator.le)

    def __eq__(self, other: typing.Union["Verbosity", str, int, object]) -> bool:
        """
        Magic method for self == other.

        'eq' is a special case because 'other' MUST be object according to mypy
        """
        if other is None:
            other = DEFAULT_VERBOSITY

        if other is Ellipsis or other is inspect._empty:
            # both instances of object; can't use Ellipsis or type(ELlipsis) = ellipsis as a type hint in mypy
            # special cases where Typer instanciates its cli arguments,
            # return False or it will crash
            return False
        if not isinstance(other, (str, int, Verbosity)):
            raise TypeError(f"Object of type {type(other)} can not be compared with Verbosity")
        return self._compare(self, other, operator.eq)

    def __hash__(self) -> int:
        """
        Magic method for `hash(self)`, also required for Typer to work.
        """
        return hash(self.value)


Verbosity_Comparable = Verbosity | str | int

DEFAULT_VERBOSITY = Verbosity.normal


class AbstractConfig(configuraptor.TypedConfig, configuraptor.Singleton):
    """
    Used by state.config and plugin configs.
    """

    _strict = True


DB_Types: typing.Any = create_enum_from_literal("DBType", SUPPORTED_DATABASE_TYPES_WITH_ALIASES)


# @dataclass
class Config(AbstractConfig):
    """
    Used as typed version of the [tool.pydal2sql] part of pyproject.toml.

    Also accessible via state.config
    """

    # settings go here
    db_type: typing.Optional[SUPPORTED_DATABASE_TYPES_WITH_ALIASES] = postpone()
    tables: Optional[list[str]] = None
    magic: bool = False
    function: str = "define_tables"
    format: SUPPORTED_OUTPUT_FORMATS = DEFAULT_OUTPUT_FORMAT
    dialect: typing.Optional[SUPPORTED_DATABASE_TYPES_WITH_ALIASES] = alias("db_type")
    input: Optional[str] = None
    output: Optional[str] = None
    noop: bool = False

    pyproject: typing.Optional[str] = None


MaybeConfig = Optional[Config]


def _get_pydal2sql_config(overwrites: dict[str, Any], toml_path: Optional[str | Path] = None) -> MaybeConfig:
    """
    Parse the users pyproject.toml (found using black's logic) and extract the tool.pydal2sql part.

    The types as entered in the toml are checked using _ensure_types,
    to make sure there isn't a string implicitly converted to a list of characters or something.

    Args:
        overwrites: cli arguments can overwrite the config toml.
        toml_path: by default, black will search for a relevant pyproject.toml.
                    If a toml_path is provided, that file will be used instead.
    """
    if toml_path is None:
        toml_path = find_pyproject_toml()

    if not toml_path:
        return None

    with open(toml_path, "rb") as f:
        full_config = tomli.load(f)

    tool_config = full_config["tool"]

    config = configuraptor.load_into(Config, tool_config, key="pydal2sql")

    config.update(pyproject=str(toml_path))
    config.update(**overwrites)

    return config


def get_pydal2sql_config(toml_path: str = None, verbosity: Verbosity = DEFAULT_VERBOSITY, **overwrites: Any) -> Config:
    """
    Load the relevant pyproject.toml config settings.

    Args:
        verbosity: if something goes wrong, level 3+ will show a warning and 4+ will raise the exception.
        toml_path: --config can be used to use a different file than ./pyproject.toml
        overwrites (dict[str, Any): cli arguments can overwrite the config toml.
                If a value is None, the key is not overwritten.
    """
    # strip out any 'overwrites' with None as value
    overwrites = configuraptor.convert_config(overwrites)

    try:
        if config := _get_pydal2sql_config(overwrites, toml_path=toml_path):
            return config
        raise ValueError("Falsey config?")
    except Exception as e:
        # something went wrong parsing config, use defaults
        if verbosity > 3:
            # verbosity = debug
            raise e
        elif verbosity > 2:
            # verbosity = verbose
            print("Error parsing pyproject.toml, falling back to defaults.", file=sys.stderr)
        return Config(**overwrites)


@dataclass()
class ApplicationState:
    """
    Application State - global user defined variables.

    State contains generic variables passed BEFORE the subcommand (so --verbosity, --config, ...),
    whereas Config contains settings from the config toml file, updated with arguments AFTER the subcommand
    (e.g. pydal2sql subcommand <directory> --flag), directory and flag will be updated in the config and not the state.

    To summarize: 'state' is applicable to all commands and config only to specific ones.
    """

    verbosity: Verbosity = DEFAULT_VERBOSITY
    config_file: Optional[str] = None  # will be filled with black's search logic
    config: MaybeConfig = None

    def __post_init__(self) -> None:
        """
        Runs after the dataclass init.
        """

    def load_config(self, **overwrites: Any) -> Config:
        """
        Load the pydal2sql config from pyproject.toml (or other config_file) with optional overwriting settings.

        Also updates attached plugin configs.
        """
        if "verbosity" in overwrites:
            self.verbosity = overwrites["verbosity"]
        if "config_file" in overwrites:
            self.config_file = overwrites.pop("config_file")

        self.config = get_pydal2sql_config(toml_path=self.config_file, **overwrites)
        return self.config

    def get_config(self) -> Config:
        """
        Get a filled config instance.
        """
        return self.config or self.load_config()

    def update_config(self, **values: Any) -> Config:
        """
        Overwrite default/toml settings with cli values.

        Example:
            `config = state.update_config(directory='src')`
            This will update the state's config and return the same object with the updated settings.
        """
        existing_config = self.get_config()

        values = configuraptor.convert_config(values)
        existing_config.update(**values)
        return existing_config


state = ApplicationState()
