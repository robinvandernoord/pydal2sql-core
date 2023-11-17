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


class MyTable(TypedTable):
    name: str
    age = IntegerField(default=0, represent=something)


class Relates(TypedTable):
    table: MyTable
    user = ReferenceField("auth_user")


def define_td_tables(_=None):
    db.define(MyTable)
    db.define(Relates)
