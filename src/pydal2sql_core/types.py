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

SUPPORTED_OUTPUT_FORMATS = typing.Literal["default", "edwh-migrate"] | None
DEFAULT_OUTPUT_FORMAT: SUPPORTED_OUTPUT_FORMATS = "default"


class SQLAdapter(_SQLAdapter):  # type: ignore
    """
    Typing friendly version of pydal's SQL Adapter.
    """


empty = Empty()


# class DummyMetaDAL(pydal.base.MetaDAL):
#     def __call__(self, *args, **kwargs):
#         # warnings.warn("Prevented use of actual DB queries in migration.")
#         # print('meta call', args, kwargs)
#         return super().__call__(*args, **kwargs)


# BLACKLIST = set()


class CustomAdapter(SQLAdapter):
    drivers = ("sqlite3",)

    def id_query(self, _: Any) -> Empty:
        warnings.warn("Prevented attempt to execute query while migrating.")
        return empty

    def execute(self, *_: Any, **__: Any) -> Empty:
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
        # print('get attribute', item)
        # if item in BLACKLIST:
        #     # print('blacklist')
        #     return empty

        if item == "_adapter":
            # print(self._drivers_available)
            return CustomAdapter(self, "", adapter_args={"driver": "sqlite3"}, driver_args="")

        value = super().__getattribute__(item)

        # print('found', value)
        return value

    # def __getitem__(self, item: str):
    #     print('get item', item)
    #     return empty

    def __call__(self, *_: Any, **__: Any) -> Empty:
        # warnings.warn("Prevented use of actual DB queries in migration.")
        # print('inst call', args, kwargs)
        return empty


# db.define_table('my_table')
# from package import imported
#
# db.define_table('my_table', Field('some_string', validator=some_external_variable, default=imported))
