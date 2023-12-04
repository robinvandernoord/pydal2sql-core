"""
Main functionality.
"""
import pickle  # nosec: B403
import typing
from pathlib import Path
from typing import Any

from pydal.adapters import MySQL, Postgre, SQLite
from pydal.dialects import Dialect, MySQLDialect, PostgreDialect, SQLiteDialect
from pydal.migrator import Migrator
from pydal.objects import Table

from .helpers import TempdirOrExistingDir, get_typing_args
from .types import (
    SUPPORTED_DATABASE_TYPES,
    SUPPORTED_DATABASE_TYPES_WITH_ALIASES,
    CustomAdapter,
    DummyDAL,
    SQLAdapter,
)


def _build_dummy_migrator(_driver_name: SUPPORTED_DATABASE_TYPES_WITH_ALIASES, /, db_folder: str) -> Migrator:
    """
    Create a Migrator specific to the sql dialect of _driver_name.
    """
    db = DummyDAL(None, migrate=False, folder=db_folder)

    aliases = {
        "postgresql": "psycopg2",
        "postgres": "psycopg2",
        "psql": "psycopg2",
        "sqlite": "sqlite3",
        "sqlite:memory": "sqlite3",
        "mysql": "pymysql",
    }

    driver_name = _driver_name.lower()
    driver_name = aliases.get(driver_name, driver_name)

    if driver_name not in get_typing_args(SUPPORTED_DATABASE_TYPES):
        raise ValueError(
            f"Unsupported database type {driver_name}. "
            f"Choose one of {get_typing_args(SUPPORTED_DATABASE_TYPES_WITH_ALIASES)}"
        )

    adapters_per_database: dict[str, typing.Type[SQLAdapter]] = {
        "psycopg2": Postgre,
        "sqlite3": SQLite,
        "pymysql": MySQL,
    }

    dialects_per_database: dict[str, typing.Type[Dialect]] = {
        "psycopg2": PostgreDialect,
        "sqlite3": SQLiteDialect,
        "pymysql": MySQLDialect,
    }

    adapter_cls = adapters_per_database[driver_name]

    installed_driver = db._drivers_available.get(driver_name)

    if not installed_driver:  # pragma: no cover
        raise ValueError(f"Please install the correct driver for database type {driver_name}")

    sql_dialect = dialects_per_database[driver_name]

    class DummyAdapter(CustomAdapter):
        types = adapter_cls.types
        driver = installed_driver
        dbengine = adapter_cls.dbengine

        commit_on_alter_table = True

    adapter = DummyAdapter(db, "", adapter_args={"driver": installed_driver})

    adapter.dialect = sql_dialect(adapter)
    db._adapter = adapter

    return Migrator(adapter)


def generate_create_statement(
    define_table: Table, db_type: SUPPORTED_DATABASE_TYPES_WITH_ALIASES = None, *, db_folder: str = None
) -> str:
    """
    Given a Table object (result of `db.define_table('mytable')` or simply db.mytable) \
       and a db type (e.g. postgres, sqlite, mysql), generate the `CREATE TABLE` SQL for that dialect.

    If no db_type is supplied, the type is guessed from the specified table.
       However, your db_type can differ from the current database used.
       You can even use a dummy database to generate SQL code with:
       `db = pydal.DAL(None, migrate=False)`

    db_folder is the database folder where migration (`.table`) files are stored.
       By default, a random temporary dir is created.
    """
    if not db_type:
        db_type = getattr(define_table._db, "_dbname", None)

        if db_type is None:
            raise ValueError("Database dialect could not be guessed from code; Please manually define a database type!")

    with TempdirOrExistingDir(db_folder) as db_folder:
        migrator = _build_dummy_migrator(db_type, db_folder=db_folder)

        sql: str = migrator.create_table(
            define_table,
            migrate=False,
            fake_migrate=True,
        )

        return sql


def sql_fields_through_tablefile(
    define_table: Table,
    db_folder: typing.Optional[str | Path] = None,
    db_type: SUPPORTED_DATABASE_TYPES_WITH_ALIASES = None,
) -> dict[str, Any]:
    """
    Generate SQL fields for the given `Table` object by simulating migration via a table file.

    Args:
        define_table (Table): The `Table` object representing the table for which SQL fields are generated.
        db_folder (str or Path, optional): The path to the database folder or directory to use. If not specified,
            a temporary directory is used for the operation. Defaults to None.
        db_type (str or SUPPORTED_DATABASE_TYPES_WITH_ALIASES, optional): The type of the database (e.g., "postgres",
            "mysql", etc.). If not provided, the database type will be guessed based on the `define_table` object.
            If the guess fails, a ValueError is raised. Defaults to None.

    Returns:
        dict[str, Any]: A dictionary containing the generated SQL fields for the `Table` object. The keys
        of the dictionary are field names, and the values are additional field information.

    Raises:
        ValueError: If the `db_type` is not provided, and it cannot be guessed from the `define_table` object.
    """
    if not db_type:
        db_type = getattr(define_table._db, "_dbname", None)

        if db_type is None:
            raise ValueError("Database dialect could not be guessed from code; Please manually define a database type!")

    with TempdirOrExistingDir(db_folder) as db_folder:
        migrator = _build_dummy_migrator(db_type, db_folder=db_folder)

        migrator.create_table(
            define_table,
            migrate=True,
            fake_migrate=True,
        )

        with (Path(db_folder) / define_table._dbt).open("rb") as tfile:
            loaded_tables = pickle.load(tfile)  # nosec B301

    return typing.cast(dict[str, Any], loaded_tables)


def generate_alter_statement(
    define_table_old: Table,
    define_table_new: Table,
    /,
    db_type: SUPPORTED_DATABASE_TYPES_WITH_ALIASES = None,
    *,
    db_folder: str = None,
) -> str:
    """
    Generate SQL ALTER statements to update the `define_table_old` to `define_table_new`.

    Args:
        define_table_old (Table): The `Table` object representing the old version of the table.
        define_table_new (Table): The `Table` object representing the new version of the table.
        db_type (str or SUPPORTED_DATABASE_TYPES_WITH_ALIASES, optional): The type of the database (e.g., "postgres",
            "mysql", etc.). If not provided, the database type will be guessed based on the `_db` attribute of the
            `define_table_old` and `define_table_new` objects.
            If the guess fails, a ValueError is raised. Defaults to None.
        db_folder (str, optional): The path to the database folder or directory to use. If not specified,
            a temporary directory is used for the operation. Defaults to None.

    Returns:
        str: A string containing SQL ALTER statements that update the `define_table_old` to `define_table_new`.

    Raises:
        ValueError: If the `db_type` is not provided, and it cannot be guessed from the `define_table_old` and
        `define_table_new` objects.
    """
    if not db_type:
        db_type = getattr(define_table_old._db, "_dbname", None) or getattr(define_table_new._db, "_dbname", None)

        if db_type is None:
            raise ValueError("Database dialect could not be guessed from code; Please manually define a database type!")

    result = ""

    # other db_folder than new!
    old_fields = sql_fields_through_tablefile(define_table_old, db_type=db_type, db_folder=None)

    with TempdirOrExistingDir(db_folder) as db_folder:
        db_folder_path = Path(db_folder)
        new_fields = sql_fields_through_tablefile(define_table_new, db_type=db_type, db_folder=db_folder)

        migrator = _build_dummy_migrator(db_type, db_folder=db_folder)

        sql_log = db_folder_path / "sql.log"
        sql_log.unlink(missing_ok=True)  # remove old crap

        original_db_old = define_table_old._db
        original_db_new = define_table_new._db
        try:
            define_table_old._db = migrator.db
            define_table_new._db = migrator.db

            migrator.migrate_table(
                define_table_new,
                new_fields,
                old_fields,
                new_fields,
                str(db_folder_path / "<deprecated>"),
                fake_migrate=True,
            )

            if not sql_log.exists():
                # no changes!
                return ""

            with sql_log.open() as f:
                for line in f:
                    if not line.startswith(("ALTER", "UPDATE")):
                        continue

                    result += line
        finally:
            define_table_new._db = original_db_new
            define_table_old._db = original_db_old

    return result


def generate_sql(
    define_table: Table,
    define_table_new: typing.Optional[Table] = None,
    /,
    db_type: SUPPORTED_DATABASE_TYPES_WITH_ALIASES = None,
    *,
    db_folder: str = None,
) -> str:
    """
    Generate SQL statements based on the provided `Table` object or a comparison of two `Table` objects.

    If `define_table_new` is provided, the function generates ALTER statements to update `define_table` to
    `define_table_new`. If `define_table_new` is not provided, the function generates CREATE statements for
    `define_table`.

    Args:
        define_table (Table): The `Table` object representing the table to generate SQL for.
        define_table_new (Table, optional): The `Table` object representing the new version of the table
            (used to generate ALTER statements). Defaults to None.
        db_type (str or SUPPORTED_DATABASE_TYPES_WITH_ALIASES, optional): The type of the database (e.g., "postgres",
            "mysql", etc.). If not provided, the database type will be guessed based on the `_db` attribute of the
            `define_table` object. If the guess fails, a ValueError is raised. Defaults to None.
        db_folder (str, optional): The path to the database folder or directory to use. If not specified,
            a temporary directory is used for the operation. Defaults to None.

    Returns:
        str: A string containing the generated SQL statements.

    Raises:
        ValueError: If the `db_type` is not provided, and it cannot be guessed from the `define_table` object.
    """
    if define_table_new:
        return generate_alter_statement(define_table, define_table_new, db_type=db_type, db_folder=db_folder)
    else:
        return generate_create_statement(define_table, db_type=db_type, db_folder=db_folder)
