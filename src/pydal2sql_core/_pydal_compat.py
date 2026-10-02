"""
Import shim for pydal internals across the 2026 restructure.

pydal <= 20260520 shipped adapters and dialects as `pydal.adapters` / `pydal.dialects`.
pydal 3.x (3.20260526+) moved them to `pydal.backend_base` and `pydal.backends.*`,
and renamed `Postgre` to `Postgres`. The classes themselves kept their interface.
"""

# isort: skip_file
# isort would merge the fallback imports and drop their per-line type: ignore comments.

import importlib.util

PYDAL_V3 = importlib.util.find_spec("pydal.backends") is not None

# only one branch runs per installed pydal version, so coverage is excluded for both.
# `unused-ignore` is listed because which ignores are needed depends on the installed version.
if PYDAL_V3:  # pragma: no cover
    from pydal.backend_base import (  # type: ignore[import-not-found,attr-defined,unused-ignore]
        Dialect,
        SQLAdapter,
        SQLDialect,
    )
    from pydal.backends.mysql import (  # type: ignore[import-not-found,attr-defined,unused-ignore]
        MySQL,
        MySQLDialect,
    )
    from pydal.backends.postgres import (  # type: ignore[import-not-found,attr-defined,unused-ignore]
        Postgres,
        PostgresDialect,
    )
    from pydal.backends.sqlite import (  # type: ignore[import-not-found,attr-defined,unused-ignore]
        SQLite,
        SQLiteDialect,
    )
else:  # pragma: no cover
    from pydal.adapters import (  # type: ignore[import-not-found,attr-defined,no-redef,unused-ignore]
        MySQL,
        SQLAdapter,
        SQLite,
    )
    from pydal.adapters import (  # type: ignore[import-not-found,attr-defined,no-redef,unused-ignore]
        Postgre as Postgres,
    )
    from pydal.dialects import (  # type: ignore[import-not-found,attr-defined,no-redef,unused-ignore]
        Dialect,
        MySQLDialect,
        SQLDialect,
        SQLiteDialect,
    )
    from pydal.dialects import (  # type: ignore[import-not-found,attr-defined,no-redef,unused-ignore]
        PostgreDialect as PostgresDialect,
    )

__all__ = [
    "PYDAL_V3",
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
