import re
import typing
from pathlib import Path

from src.pydal2sql_core.__about__ import __version__
from src.pydal2sql_core.cli_support import sql_to_function_name
from src.pydal2sql_core.helpers import TempdirOrExistingDir, flatten, get_typing_args


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
