from pydal import DAL


def define_tables(db: DAL):
    db.define_table("empty")


def define_tables_multiple_arguments(db: DAL, another: str):
    db.define_table(another)
