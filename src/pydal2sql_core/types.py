"""
Contains types for core.py.
"""
import typing
import warnings
from typing import Any

import pydal
from pydal.adapters import SQLAdapter as _SQLAdapter
from witchery import Empty

SUPPORTED_DATABASE_TYPES = typing.Literal["psycopg2", "sqlite3", "pymysql"]
DATABASE_ALIASES_PSQL = typing.Literal["postgresql", "postgres", "psql"]
DATABASE_ALIASES_SQLITE = typing.Literal["sqlite"]
DATABASE_ALIASES_MYSQL = typing.Literal["mysql"]

DATABASE_ALIASES = DATABASE_ALIASES_PSQL | DATABASE_ALIASES_SQLITE | DATABASE_ALIASES_MYSQL
SUPPORTED_DATABASE_TYPES_WITH_ALIASES = SUPPORTED_DATABASE_TYPES | DATABASE_ALIASES

_SUPPORTED_OUTPUT_FORMATS = typing.Literal["default", "edwh-migrate"]
SUPPORTED_OUTPUT_FORMATS = _SUPPORTED_OUTPUT_FORMATS | None
DEFAULT_OUTPUT_FORMAT: SUPPORTED_OUTPUT_FORMATS = "default"


class SQLAdapter(_SQLAdapter):  # type: ignore
    """
    Typing friendly version of pydal's SQL Adapter.
    """


empty = Empty()


class CustomAdapter(SQLAdapter):
    """
    Adapter that prevents actual queries.
    """

    drivers = ("sqlite3",)

    def id_query(self, _: Any) -> Empty:  # pragma: no cover
        """
        Normally generates table._id != None.
        """
        warnings.warn("Prevented attempt to execute query while migrating.")
        return empty

    def execute(self, *_: Any, **__: Any) -> Empty:
        """
        Normally executes an SQL query on the adapter.
        """
        warnings.warn("Prevented attempt to execute query while migrating.")
        return empty

    @property
    def cursor(self) -> Empty:
        """
        Trying to connect to the database.
        """
        warnings.warn("Prevented attempt to execute query while migrating.")
        return empty


class DummyDAL(pydal.DAL):  # type: ignore
    """
    Subclass of DAL that disables committing.
    """

    def commit(self) -> None:
        """
        Do Nothing.
        """

    def __getattribute__(self, item: str) -> Any:
        """
        Replace dal._adapter with a custom adapter that doesn't run queries.
        """
        if item == "_adapter":
            return CustomAdapter(self, "", adapter_args={"driver": "sqlite3"}, driver_args="")

        return super().__getattribute__(item)

    def __call__(self, *_: Any, **__: Any) -> Empty:
        """
        Prevents calling db() and thus creating a query.
        """
        return empty


try:
    import typedal

    class DummyTypeDAL(typedal.TypeDAL, DummyDAL):
        """
        Variant of DummyDAL for TypeDAL.
        """

        def __init__(self, *args: Any, **settings: Any) -> None:
            """
            Force TypeDAL to ignore project/env settings.
            """
            # dummy typedal should not look at these settings:
            settings["use_pyproject"] = False
            settings["use_env"] = False
            if not settings.get("folder"):
                settings["folder"] = "/tmp/typedal2sql"

            super().__init__(*args, **settings)

except ImportError:  # pragma: no cover
    DummyTypeDAL = DummyDAL  # type: ignore
