"""
Imports from pydal internals whose location depends on the installed pydal version.

pydal 20261107.0 merged the `adapters`, `dialects`, `parsers` and `representers` packages into
`pydal.backend_base` (the shared base classes) and `pydal.backends` (one module per database), and renamed
`Postgre` / `PostgreDialect` to `Postgres` / `PostgresDialect`. The classes kept their behavior,
so only the import locations differ.
"""

from importlib.util import find_spec

# True on pydal >= 20261107.0; False on the older `pydal.adapters` / `pydal.dialects` layout.
PYDAL_BACKENDS_LAYOUT = find_spec("pydal.backend_base") is not None

# Only one of these branches runs in a given environment; CI covers both by testing against both pydal layouts.
if PYDAL_BACKENDS_LAYOUT:  # pragma: no cover
    from pydal.backend_base import Dialect, SQLAdapter, SQLDialect
    from pydal.backends.mysql import MySQL, MySQLDialect
    from pydal.backends.postgres import Postgres, PostgresDialect
    from pydal.backends.sqlite import SQLite, SQLiteDialect
else:  # pragma: no cover
    from pydal.adapters import MySQL, SQLAdapter, SQLite
    from pydal.adapters import Postgre as Postgres
    from pydal.dialects import Dialect, MySQLDialect, SQLDialect, SQLiteDialect
    from pydal.dialects import PostgreDialect as PostgresDialect

__all__ = [
    "PYDAL_BACKENDS_LAYOUT",
    "Dialect",
    "MySQL",
    "MySQLDialect",
    "Postgres",
    "PostgresDialect",
    "SQLAdapter",
    "SQLDialect",
    "SQLite",
    "SQLiteDialect",
]
