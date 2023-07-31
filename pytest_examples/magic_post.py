# this is the changed file
from pydal import DAL

my_method = SomeClass()["first"]

db = DAL("sqlite://my_real_database")

db.define_table(
    "person",
    Field("name", "text", notnull=True, default=my_method.new_uuid()),
    Field("birthday", "datetime", default=datetime.datetime.utcnow()),
    Field("location", "string"),
)

db.define_table("empty")


db.define_table("new_table", Field("new_field"))

db_type = "psql"
