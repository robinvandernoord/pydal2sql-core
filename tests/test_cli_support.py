import os
import shutil
import textwrap
from pathlib import Path

import pytest
from contextlib_chdir import chdir

from src.pydal2sql_core.cli_support import (
    ensure_no_migrate_on_real_db,
    extract_file_versions_and_paths,
    find_git_root,
    get_absolute_path_info,
    get_file_for_version,
    handle_cli,
)
from src.pydal2sql_core.helpers import TempdirOrExistingDir
from tests.mock_git import mock_git


def test_extract_file_versions_and_paths():
    with pytest.raises(ValueError):
        extract_file_versions_and_paths("", "")

    (version1, name1), (version2, name2) = extract_file_versions_and_paths("my.file", "")

    assert name1 == name2
    assert version1 == "latest"
    assert version2 == "current"

    (version1, name1), (version2, name2) = extract_file_versions_and_paths("", "my.file")

    assert name1 == name2
    assert version1 == "latest"
    assert version2 == "current"

    (version1, name1), (version2, name2) = extract_file_versions_and_paths("@development", "my.file@latest")

    assert name1 == name2
    assert version1 == "development"
    assert version2 == "latest"

    (version1, name1), (version2, name2) = extract_file_versions_and_paths("-", "my.file@latest")

    assert name1 != name2
    assert version1 == "stdin"
    assert version2 == "latest"


def test_ensure_no_migrate_on_real_db():
    # test local import:

    code = textwrap.dedent(
        """
    from .common import db

    database.define_tables('something_else')
    """
    )

    target = textwrap.dedent(
        """
    database.define_tables('something_else')
    """
    )

    with pytest.raises(ValueError):
        ensure_no_migrate_on_real_db(code, fix=False)

    assert ensure_no_migrate_on_real_db(code, fix=True).strip() == target.strip()

    # test local import AND definition:

    code = textwrap.dedent(
        """
    from .common import db
    
    database = DAL()
    
    db.define_tables('something')
    database.define_tables('something_else')
    """
    )

    target = textwrap.dedent(
        """
    db.define_tables('something')
    database.define_tables('something_else')
    """
    )

    with pytest.raises(ValueError):
        ensure_no_migrate_on_real_db(code, fix=False)

    assert ensure_no_migrate_on_real_db(code, fix=True).strip() == target.strip()


def test_git_support():
    with mock_git():
        file_contents = get_file_for_version("magic.py", "current")

        assert "this is the changed file" in file_contents

        file_contents = get_file_for_version("magic.py", "latest")

        assert "this is the original file" in file_contents

        file_contents = get_file_for_version("magic.py", "master")

        assert "this is the original file" in file_contents

        os.mkdir("nested")
        with chdir("nested"):
            exists, path = get_absolute_path_info("-", "stdin")
            assert exists
            exists, path = get_absolute_path_info("magic.py", "...")
            assert exists
            assert path and "nested" not in path

            exists, path = get_absolute_path_info(None, "")
            assert not exists

            exists, path = get_absolute_path_info("nested_magic.py", "...")
            assert not exists

            shutil.copy("../magic.py", "nested_magic.py")
            exists, path = get_absolute_path_info("nested_magic.py", "...")
            assert exists
            assert "nested/nested_magic.py" in path

    with TempdirOrExistingDir() as cwd, chdir(cwd):
        Path("pyproject.toml").touch()
        assert find_git_root() is None


def test_handle_cli(capsys):
    # only `handle_cli` output is tested here,
    # actual create/alter statements are fully tested in test_core.py.

    before = textwrap.dedent(
        """
        db.define_table('my_table')
        """
    )

    after = textwrap.dedent(
        """
        db.define_table('my_table', Field('some_string'))
        """
    )

    assert handle_cli(before, after, db_type="psql")
    captured = capsys.readouterr()
    assert "ALTER TABLE" in captured.out
    assert not captured.err
    assert handle_cli(before, after, db_type="psql", verbose=True)
    captured = capsys.readouterr()
    assert "ALTER TABLE" in captured.out
    assert captured.err  # due to verbose

    before = textwrap.dedent(
        """
        db.define_table('my_table')
        """
    )

    after = textwrap.dedent(
        """
        from package import imported
        
        db.define_table('my_table', Field('some_string', validator=some_external_variable, default=imported))
        """
    )

    # no magic -> no success
    assert not handle_cli(before, after, db_type="psql")
    captured = capsys.readouterr()
    assert "ALTER TABLE" not in captured.out
    assert captured.err

    assert handle_cli(before, after, db_type="psql", magic=True)
    captured = capsys.readouterr()
    assert "ALTER TABLE" in captured.out
    assert not captured.err

    # in a function

    before = textwrap.dedent(
        """
        def define_tables(db):
            db.define_table('my_table')
        """
    )

    after = textwrap.dedent(
        """
        def define_tables(db):
            db.define_table('my_table', Field('some_string', validator=something))
        """
    )

    assert handle_cli(before, after, db_type="psql", magic=True, verbose=False)
    captured = capsys.readouterr()

    assert "ALTER TABLE" in captured.out
    assert not captured.err

    assert handle_cli(before, after, db_type="psql", magic=True, verbose=False, function_name="define_tables")
    captured = capsys.readouterr()

    assert "ALTER TABLE" in captured.out
    assert not captured.err

    assert not handle_cli(
        before, after, db_type="psql", magic=True, verbose=False, function_name="define_something_else"
    )
    captured = capsys.readouterr()

    assert not captured.out
    assert "No tables found in the top-level or define_something_else function!" in captured.err

    assert handle_cli(before, after, noop=True)
    captured = capsys.readouterr()

    assert "def define_tables" in captured.err
    assert not captured.out
