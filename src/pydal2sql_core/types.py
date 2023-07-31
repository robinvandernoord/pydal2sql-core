"""
Contains types for core.py.
"""
import typing

SUPPORTED_DATABASE_TYPES = typing.Literal["psycopg2", "sqlite3", "pymysql"]
DATABASE_ALIASES_PSQL = typing.Literal["postgresql", "postgres", "psql"]
DATABASE_ALIASES_SQLITE = typing.Literal["sqlite"]
DATABASE_ALIASES_MYSQL = typing.Literal["mysql"]

DATABASE_ALIASES = DATABASE_ALIASES_PSQL | DATABASE_ALIASES_SQLITE | DATABASE_ALIASES_MYSQL
SUPPORTED_DATABASE_TYPES_WITH_ALIASES = SUPPORTED_DATABASE_TYPES | DATABASE_ALIASES
