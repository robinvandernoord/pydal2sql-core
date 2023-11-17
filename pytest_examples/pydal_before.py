from typedal.fields import ReferenceField, IntegerField
import veryfake

import os
import json
import httpx

import typing
import attrs
from attrs import define, field, Factory, asdict, evolve
import copy
import shlex
import hashlib
import random
from pydal.objects import Rows

if typing.TYPE_CHECKING:
    import lorem
    from gluon import URL, auth, request
    from pydal import *
    from pydal.objects import *
    from pydal.validators import *
    from yatl import *
    from sys import something


def define_my_tables(db):
    db.define_table("my_table",
              Field("name", represent=something),
              )

    db.define_table("relates",
              Field("table", "references my_table"),
              Field("user", "references auth_user"),
              )
