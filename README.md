# pydal2sql-core

[![PyPI - Version](https://img.shields.io/pypi/v/pydal2sql-core.svg)](https://pypi.org/project/pydal2sql-core)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pydal2sql-core.svg)](https://pypi.org/project/pydal2sql-core)  
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[![su6 checks](https://github.com/robinvandernoord/pydal2sql-core/actions/workflows/su6.yml/badge.svg?branch=development)](https://github.com/robinvandernoord/pydal2sql-core/actions)
![coverage.svg](coverage.svg)

-----

Companion library for [`pydal2sql`](https://github.com/robinvandernoord/pydal2sql) containing the actual logic.
The other library only serves as a Typer-based CLI front-end.

_More Documentation coming soon!_

## Table of Contents

- [Installation](#installation)
- [As a Python Library](#as-a-python-library)
- [License](#license)

## Installation

```bash
pip install pydal2sql-core
```

## As a Python Library

`pydal2sql-core` also exposes a `generate_sql` method that can perform the same actions on one (for CREATE) or two (for
ALTER) `pydal.Table` objects when used within Python.

```python
from pydal import DAL, Field
from pydal2sql_core import generate_sql

db = DAL(None, migrate=False)  # <- without running database or with a different type of database

person_initial = db.define_table(
    "person",
    Field(
        "name",
        "string",
        notnull=True,
    ),
    Field("age", "integer", default=18),
    Field("float", "decimal(2,3)"),
    Field("nicknames", "list:string"),
    Field("obj", "json"),
)

print(
    generate_sql(
        db.person, db_type="psql"  # or sqlite, or mysql; Optional with fallback to currently using database type.
    )
)
```

```sql
CREATE TABLE person
(
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      VARCHAR(512),
    age       INTEGER,
    float     NUMERIC(2, 3),
    nicknames TEXT,
    obj       TEXT
);
```

```python
person_new = db.define_table(
    "person",
    Field(
        "name",
        "text",
    ),
    Field("birthday", "datetime"),
    redefine=True
)

generate_sql(
    person_initial,
    person_new,
    db_type="psql"
)
```

```sql
ALTER TABLE person
    ADD "name__tmp" TEXT;
UPDATE person
SET "name__tmp"=name;
ALTER TABLE person DROP COLUMN name;
ALTER TABLE person
    ADD name TEXT;
UPDATE person
SET name="name__tmp";
ALTER TABLE person DROP COLUMN "name__tmp";
ALTER TABLE person
    ADD birthday TIMESTAMP;
ALTER TABLE person DROP COLUMN age;
ALTER TABLE person DROP COLUMN float;
ALTER TABLE person DROP COLUMN nicknames;
ALTER TABLE person DROP COLUMN obj;
```

## License

`pydal2sql-core` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
