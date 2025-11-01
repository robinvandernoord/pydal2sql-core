import re
import typing
from pathlib import Path

from src.pydal2sql_core.__about__ import __version__
from src.pydal2sql_core.cli_support import sql_to_function_name
from src.pydal2sql_core.helpers import TempdirOrExistingDir, detect_typedal, excl, flatten, get_typing_args, uniq


def test_about():
    version_re = re.compile(r"\d+\.\d+\.\d+.*")
    assert version_re.findall(__version__)


def test_flatten():
    assert flatten([[1], [2, [3]]]) == [1, 2, 3]
    assert flatten([["12"], ["2", ["3"]]]) == ["12", "2", "3"]


def test_get_typing_args():
    assert get_typing_args(typing.Union["str", str, typing.Literal["str", "int"]]) == [str, str, "str", "int"]


def test_TempdirOrExistingDir():
    with TempdirOrExistingDir() as temp_dir:
        assert isinstance(temp_dir, str)
        temp_dir.startswith("/tmp")

    with TempdirOrExistingDir("real_dir") as real_dir:
        assert real_dir == "real_dir"

    with TempdirOrExistingDir(Path("real_dir")) as real_dir:
        assert real_dir == str(Path("real_dir"))


def test_sql_to_function_name():
    assert (
        sql_to_function_name(
            """
            -- user
        CREATE TABLE user(
            id SERIAL PRIMARY KEY,
            name VARCHAR(512) NOT NULL,
            age INTEGER NOT NULL
        );
    """
        )
        == "create_user"
    )

    assert (
        sql_to_function_name(
            """
    ALTER TABLE user
        ADD COLUMN email VARCHAR(255);
    """
        )
        == "alter_user"
    )

    assert (
        sql_to_function_name(
            """
     DROP TABLE user;
     """
        )
        == "drop_user"
    )

    assert (
        sql_to_function_name(
            """
     DELETE FROM products WHERE category = 'OldCategory';
     """
        )
        == "unknown_migration"
    )


def test_uniq():
    assert uniq([1, 2, 3, 3, 2, 1]) == [1, 2, 3]
    assert uniq([3, 2, 1, 3, 1, 2]) == [3, 2, 1]


def test_excl():
    assert excl([1, 2, 3, 4, 3, 2, 1], [1, 2]) == [3, 4, 3]
    assert excl([1, 2, 3, 4, 3, 2, 1], 4) == [1, 2, 3, 3, 2, 1]


def test_detect_typedal():
    # Basic import styles
    assert detect_typedal("import typedal")
    assert detect_typedal("import typedal as dal")
    assert detect_typedal("from typedal import Something")
    assert detect_typedal("from typedal.submodule import Thing")
    assert detect_typedal("from typedal.sub.module.deep import Thing")

    # Multiple imports with typedal
    assert detect_typedal("import os, typedal, sys")
    assert detect_typedal("import typedal\nimport os")
    assert detect_typedal("""
    import os
    import typedal
    from collections import defaultdict
        """)

    # From imports with multiple names
    assert detect_typedal("from typedal import Thing1, Thing2, Thing3")
    assert detect_typedal("from typedal import Something as ST, Other as OT")

    # Star import
    assert detect_typedal("from typedal import *")

    # Multiline import
    assert detect_typedal("""
    from typedal import (
        Something,
        SomethingElse,
        YetAnother
    )
        """)

    # Imports inside code blocks
    assert detect_typedal("""
    def foo():
        import typedal
        return typedal
        """)

    assert detect_typedal("""
    if True:
        import typedal
        """)

    assert detect_typedal("""
    try:
        import typedal
    except ImportError:
        pass
        """)

    # Duplicate imports
    assert detect_typedal("""
    import typedal
    import typedal
    from typedal import X
    from typedal import Y
        """)

    # With whitespace
    assert detect_typedal("    import typedal\n")
    assert detect_typedal("""
                import typedal
                from os import path
        """)

    # Comments and strings don't count
    assert not detect_typedal("# import typedal")
    assert not detect_typedal('"import typedal"')
    assert not detect_typedal("'''import typedal'''")
    assert not detect_typedal("""
    # import typedal
    "import typedal"
    import os
        """)

    # No imports
    assert not detect_typedal("")
    assert not detect_typedal("x = 10")
    assert not detect_typedal("""
    def foo():
        return 42
        """)

    # Other modules only
    assert not detect_typedal("import os")
    assert not detect_typedal("from collections import Counter")
    assert not detect_typedal("import sys, os, json")

    # Syntax errors
    assert not detect_typedal("import this is not valid")
    assert not detect_typedal("import typedal\nif True:")

    # Similar names but not typedal
    assert not detect_typedal("import typedal_other")
    assert not detect_typedal("import not_typedal")
    assert not detect_typedal("from typedal_similar import X")

    # Relative imports
    assert not detect_typedal("from . import something")
    assert not detect_typedal("from .. import something")
