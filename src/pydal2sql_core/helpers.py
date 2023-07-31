"""
Contains helpers for core.
"""

import tempfile
import types
import typing
from contextlib import contextmanager
from pathlib import Path

T = typing.TypeVar("T", bound=typing.Any)
Recurse = typing.Union[T, typing.Iterable["Recurse[T]"]]


def _flatten(xs: typing.Iterable[T | Recurse[T]]) -> typing.Generator[T, None, None]:
    """
    Flatten recursively.
    """
    for x in xs:
        if isinstance(x, typing.Iterable) and not isinstance(x, (str, bytes)):
            yield from _flatten(x)
        else:
            yield typing.cast(T, x)


def flatten(it: Recurse[T]) -> list[T]:
    """
    Turn an arbitrarily nested iterable into a flat (1d) list.

    Example:
        [[[1]], 2] -> [1, 2]
    """
    generator = _flatten(it)
    return list(generator)


ANY_TYPE = type | types.UnionType | typing.Type[typing.Any] | typing._SpecialForm


def _get_typing_args_recursive(some: ANY_TYPE) -> list[type]:
    """
    Recursively extract types from parameterized types such as unions or generics.

    Note:
        The return type is actually a nested list of types and strings!
        Please use `get_typing_args`, which calls flatten to create a 1D list of types and strings.

        get_typing_args_recursive(
            typing.Union["str", typing.Literal["Joe"]]
        )

        -> [[<class 'str'>], [['Joe']]]
    """
    if args := typing.get_args(some):
        return [_get_typing_args_recursive(_) for _ in args]  # type: ignore # due to recursion

    # else: no args -> it's just a type!
    if isinstance(some, typing.ForwardRef):
        return [
            # ForwardRef<str> -> str
            some._evaluate(globals(), locals(), set())
        ]

    return [typing.cast(type, some)]


def get_typing_args(some: ANY_TYPE) -> list[type | str]:
    """
    Extract typing.get_args for Unions, Literals etc.

    Useful for e.g.  getting the values of Literals'
    """
    return flatten(
        _get_typing_args_recursive(some),
    )


@contextmanager
def TempdirOrExistingDir(folder_path: typing.Optional[str | Path] = None) -> typing.Generator[str, None, None]:
    """
    Either use db_folder or create a tempdir.

    The tempdir will be removed on exit, your original folder_path will not be modified in that regard.

    Example:
        with TempdirOrExistingDir() as my_path: ...
    """
    if folder_path is None:
        tmp_dir = tempfile.TemporaryDirectory()
        yield tmp_dir.name
    elif isinstance(folder_path, Path):
        yield str(folder_path)
    else:
        yield folder_path
