import io
import os
import shutil
import tempfile
import textwrap
from pathlib import Path

import pytest
from contextlib_chdir import chdir

from src.pydal2sql_core.cli_support import (
    _handle_output,
    core_alter,
    core_create,
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


def test_dummy_dal():
    code = """
    tab = db.define_table(
        "my_table",
        Field('string')
    )
    
    assert not db(db.my_table).count().fake
    
    assert not db.my_table.insert()
    
    assert not db.my_table.truncate()
    
    """
    assert handle_cli("", textwrap.dedent(code), magic=True, db_type="sqlite")


def test_dummy_typedal():
    code = """
    import typedal
    import typing
    typing.TYPE_CHECKING = True # <- should break httpx
    import httpx
    
    assert not httpx
    
    @db.define
    class MyTable(typedal.TypedTable):
        something: str
        
    assert not MyTable.insert(something='123')
        
    assert not MyTable.update(MyTable.id > 0, something='456')
    """

    assert handle_cli("", textwrap.dedent(code), magic=True, db_type="sqlite")


def test_break_cli(capsys):
    code = """
    raise RecursionError("I broke it!")
    """

    assert not handle_cli("", textwrap.dedent(code), magic=True, db_type="sqlite")
    captured = capsys.readouterr()

    assert "Code could not be fixed automagically!" in captured.err
    assert "I broke it!" in captured.err

    code = """
    raise KeyError('another one')
    """

    with pytest.raises(KeyError):
        assert not handle_cli("", textwrap.dedent(code), magic=True, db_type="sqlite")

    assert not handle_cli("", "db.define_table('test')", magic=True, db_type="sqlite", output_format="invalid")
    captured = capsys.readouterr()
    assert "invalid" in captured.err
    assert "edwh-migrate" in captured.err


def test_handle_output(capsys):
    output = io.StringIO(
        """
    CREATE TABLE users (...);
    -- END OF MIGRATION --
    
    ALTER TABLE users (...);
    -- END OF MIGRATION --
    """
    )
    with tempfile.NamedTemporaryFile() as f:
        # example 1:
        # - Path
        # - default
        # - pydal
        path = Path(f.name)
        _handle_output(output, path, output_format="default", is_typedal=False)

        with path.open() as f:
            written_data = f.read()

            # no imports or function because output format is default:
            assert "from pydal import DAL" not in written_data
            assert "from typedal import TypeDAL" not in written_data
            assert "create_users" not in written_data

            assert "CREATE TABLE users" in written_data or 'CREATE TABLE "users"' in written_data

    with tempfile.NamedTemporaryFile() as f:
        # example 2:
        # - str
        # - edwh-migrate
        # - typedal
        _handle_output(output, f.name, output_format="edwh-migrate", is_typedal=True)
        captured = capsys.readouterr()
        assert "Written migration" in captured.out

        with open(f.name) as _f:
            written_data = _f.read()

            assert "from pydal import DAL" not in written_data
            assert "from typedal import TypeDAL" in written_data
            assert "create_users" in written_data
            assert "CREATE TABLE users" in written_data
            assert "001" in written_data

        # same output again:
        _handle_output(output, f.name, output_format="edwh-migrate", is_typedal=True)
        captured = capsys.readouterr()
        assert "Nothing to write" in captured.out

        # now with a slightly different CREATE:
        # should not write
        output = io.StringIO(
            """
        CREATE TABLE users (...2);
        -- END OF MIGRATION --

        ALTER TABLE users (...);
        -- END OF MIGRATION --
        """
        )

        _handle_output(output, f.name, output_format="edwh-migrate", is_typedal=True)
        captured = capsys.readouterr()
        assert "with different contents" in captured.out
        assert "Written migration" not in captured.out

        # now with a different ALTER:
        # should bump idx
        output = io.StringIO(
            """
        CREATE TABLE users (...);
        -- END OF MIGRATION --

        ALTER TABLE users (...2);
        -- END OF MIGRATION --
        """
        )

        _handle_output(output, f.name, output_format="edwh-migrate", is_typedal=True)
        captured = capsys.readouterr()
        assert "Written migration" in captured.out

        with open(f.name) as _f:
            written_data = _f.read()

            assert "002" in written_data


def test_empty_output(capsys):
    output = io.StringIO(
        """
        -- start users --
    """
    )
    with tempfile.NamedTemporaryFile() as f:
        # example 1:
        # - Path
        # - default
        # - pydal
        path = Path(f.name)
        _handle_output(output, path, output_format="edwh-migrate", is_typedal=False)
        captured = capsys.readouterr()
        assert "Nothing to write" in captured.out

        with path.open() as f:
            written_data = f.read()

            assert "@migration" not in written_data


pytest_examples = Path("./pytest_examples").resolve()
before = str(pytest_examples / "pydal_before.py")
after = str(pytest_examples / "typedal_after.py")


def test_core_create():
    with pytest.raises(FileNotFoundError):
        assert not core_create("/tmp/fake-migration.py")

    assert not core_create(before)
    assert not core_create(before, function="define_my_tables")
    assert not core_create(before, magic=True)
    assert core_create(before, magic=True, function="define_my_tables")
    assert core_create(before, magic=True, function="define_my_tables", db_type="psql")

    assert not core_create(after)
    assert not core_create(after, magic=True)
    assert not core_create(after, db_type="sqlite")
    buffer = io.StringIO()

    assert core_create(
        f"{after}:define_td_tables",
        magic=True,
        db_type="sqlite",
        output_file=buffer,
    )
    buffer.seek(0)

    assert buffer.read().count("CREATE") == 2


def test_core_alter():
    with pytest.raises(FileNotFoundError):
        assert not core_alter("fake-first", "fake-second")

    with pytest.raises(FileNotFoundError):
        # real file, fake git branch:
        assert not core_alter(f"{before}@fake", f"{after}@fake")

    with tempfile.NamedTemporaryFile() as f:
        # f exists but empty
        assert not core_alter(f.name, f.name)

        # same contents
        p = Path(f.name)
        p.write_text("print()")
        assert not core_alter(f.name, f.name)

    assert not core_alter(before, after)
    assert not core_alter(before, after, magic=True, db_type="sqlite")
    assert not core_alter(f"{before}:define_my_tables", f"{after}:define_td_tables")
    buffer = io.StringIO()
    assert core_alter(
        f"{before}:define_my_tables",
        f"{after}:define_td_tables",
        db_type="sqlite",
        magic=True,
        output_file=buffer,
    )
    buffer.seek(0)

    contents = buffer.read()

    assert "CREATE" not in contents
    assert "ALTER" in contents
