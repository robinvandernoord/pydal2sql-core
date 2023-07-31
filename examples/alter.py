import pydal
from pydal import Field

from src.pydal2sql_core import generate_sql

if __name__ == "__main__":
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
        Field("obj", "integer"),
    )

    new = db.define_table(
        "my_table",
        Field(
            "name",
            "string",
            notnull=True,
        ),
        Field("birthday", "datetime"),  # replaced age with birthday
        # removed some properties
        Field("nicknames", "string"),  # your nickname must now be a varchar instead of text.
        # Field("obj", "json"),
        redefine=True,
    )

    print(generate_sql(old, new, db_type="sqlite"))
