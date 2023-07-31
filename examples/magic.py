my_method = SomeClass()["first"]

db.define_table(
    "person",
    Field("name", "text", notnull=True, default=my_method.new_uuid()),
    Field("birthday", "datetime", default=datetime.datetime.utcnow()),
    Field("location", "string"),
)

db.define_table("empty")

db_type = "sqlite"
