# this is the original file

my_method = SomeClass()["first"]

db.define_table(
    "person",
    Field("name", "string", nullable=False, default=my_method.new_uuid()),
    Field("birthday", "datetime", default=datetime.datetime.utcnow()),
    Field("removed"),
)

db.define_table("old_table", Field("old_field"))

db.define_table("empty")

db_type = "psql"
