import io

import pydal
import pytest
from pydal import DAL, Field
import datetime as dt
from pydal2sql_core.cli_support import core_stub
from src.pydal2sql_core import (
    SUPPORTED_DATABASE_TYPES,
    core_alter,
    core_create,
    generate_sql,
)
from src.pydal2sql_core.core import _build_dummy_migrator, sql_fields_through_tablefile
from src.pydal2sql_core.helpers import TempdirOrExistingDir


def test_create():
    db = pydal.DAL(None, migrate=False)  # <- without running database or with a different type of database

    db.define_table(
        "person",
        Field(
            "name",
            "string",
            notnull=True,
        ),
        Field("age", "integer", default=18, notnull=True),
        Field("float", "decimal(2,3)"),
        Field("nicknames", "list:string"),
        Field("obj", "json", notnull=True, default=lambda: ["exclude from default"]),
    )

    generated = {}

    with pytest.raises(ValueError):
        # db type can't be guessed if the db connection string is None and db_type is also None:
        generate_sql(db.person, db_type=None)

    id_keys = {
        "psycopg2": "id SERIAL PRIMARY KEY",
        "sqlite3": "id INTEGER PRIMARY KEY AUTOINCREMENT",
        "pymysql": "id INT AUTO_INCREMENT",
    }

    for database_type in SUPPORTED_DATABASE_TYPES:
        generated[database_type] = sql = generate_sql(db.person, db_type=database_type)

        assert sql

        assert id_keys[database_type] in sql
        assert "name" in sql
        assert "CHAR" in sql

        text_type = "LONGTEXT" if database_type == "pymysql" else "TEXT"

        assert f"nicknames {text_type}" in sql
        assert "age INTEGER" in sql
        assert "18" in sql  # notnull default

        assert "obj" in sql
        assert "exclude from default" not in sql  # notnull lambda default

    # sqlite
    print(generated["sqlite3"])

    # psql
    print(generated["psycopg2"])

    # mysql
    assert "ENGINE=InnoDB CHARACTER SET utf8" in generated["pymysql"]

    ### todo:
    core_create


def test_alter():
    db = pydal.DAL(None, migrate=False)  # <- without running database or with a different type of database

    old = db.define_table(
        "my_table",
        Field(
            "name",
            "string",
            notnull=False,
        ),
        Field("age", "integer", default=18),
        Field("float", "decimal(2,3)"),
        Field("nicknames", "list:string"),
        Field("obj", "json"),
    )

    new = db.define_table(
        "my_table_new",
        Field(
            "name",
            "string",
            notnull=True,
        ),
        Field("birthday", "datetime"),  # replaced age with birthday
        # removed some properties
        Field("nicknames", "string"),  # your nickname must now be a varchar instead of text.
        Field("obj", "integer"),  # total type change
    )

    assert generate_sql(old, old, db_type="psql") == ""  # no change

    alter_statements = generate_sql(old, new, db_type="psql")

    assert "NOT NULL" in alter_statements
    assert "DROP COLUMN float" in alter_statements
    assert "ADD birthday TIMESTAMP" in alter_statements

    alter_statements = generate_sql(old, new, db_type="sqlite")
    # sql only adds columns

    assert "NOT NULL" not in alter_statements
    assert "DROP COLUMN float" not in alter_statements
    assert "ADD birthday TIMESTAMP" in alter_statements

    # infer db type:
    with pytest.raises(ValueError):
        # could not infer from None DAL and None db_type:
        generate_sql(old, new, db_type=None)

    with pytest.raises(ValueError):
        sql_fields_through_tablefile(new)

    db = pydal.DAL("sqlite://:memory:", migrate=False)

    before = db.define_table("empty")

    after = db.define_table("empty", Field("empty"), redefine=True)

    assert generate_sql(before, after)

    assert sql_fields_through_tablefile(after)

    ### todo:
    core_alter


def test_invalid_dbtype():
    with pytest.raises(ValueError):
        with TempdirOrExistingDir() as temp_dir:
            _build_dummy_migrator("magicdb", db_folder=temp_dir)


def test_guess_db_type():
    with TempdirOrExistingDir() as temp_dir:
        db = DAL("sqlite://:memory:", folder=temp_dir)

        empty = db.define_table("empty")
        sql = generate_sql(empty)

        assert (
            sql.strip()
            == """CREATE TABLE "empty"(
    "id" INTEGER PRIMARY KEY AUTOINCREMENT
);""".strip()
        )


def test_core_stub_vanilla():
    output_file = io.StringIO()
    core_stub("my_unique_migration_name", output_format="default", output_file=output_file)
    output_file.seek(0)
    output_contents = output_file.read()

    assert "-- my_unique_migration_name" in output_contents

    assert "def " not in output_contents
    assert ": DAL" not in output_contents
    assert ": TypeDAL" not in output_contents


def test_core_stub_dry():
    output_file = io.StringIO()
    core_stub("my_unique_migration_name", output_format="default", output_file=output_file, dry_run=True)
    output_file.seek(0)
    output_contents = output_file.read()
    assert not output_contents


def test_core_stub_pydal():
    output_file = io.StringIO()
    core_stub("my_unique_migration_name", output_format="edwh-migrate", output_file=output_file, is_typedal=False)
    output_file.seek(0)
    output_contents = output_file.read()

    assert "my_unique_migration_name" in output_contents
    datetime = dt.datetime.utcnow()
    date = datetime.strftime("%Y%m%d")
    assert f"_{date}" in output_contents
    assert f"_001" in output_contents

    assert ": DAL" in output_contents
    assert ": TypeDAL" not in output_contents


def test_core_stub_typedal():
    output_file = io.StringIO()
    core_stub("my_unique_migration_name", output_format="edwh-migrate", output_file=output_file, is_typedal=True)
    output_file.seek(0)
    output_contents = output_file.read()

    assert "my_unique_migration_name" in output_contents
    datetime = dt.datetime.utcnow()
    date = datetime.strftime("%Y%m%d")
    assert f"_{date}" in output_contents
    assert f"_001" in output_contents

    assert ": DAL" not in output_contents
    assert ": TypeDAL" in output_contents
