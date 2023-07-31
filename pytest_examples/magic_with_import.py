import fake_library
from shared_code import db

from .common import db

db.define_table("something",
                Field("something", default=fake_library.uuid)
                )
