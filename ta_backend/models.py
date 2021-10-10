import uuid
from datetime import datetime as dt
from enum import Enum
from typing import TYPE_CHECKING, Generic

import ormar

if TYPE_CHECKING:
    from ormar.models import T
    from ormar.relations.querysetproxy import QuerysetProxy as _QSP

    class QuerysetProxy(Generic[T], _QSP, list):  # type: ignore
        ...


from ta_backend.helper.database import BaseMeta


class Subject(Enum):
    DDP = "ddp"
    MatDis = "matdis"
    Kalkulus = "kalkulus"
    PSD = "psd"
    ManBis = "manbis"
    Kombistek = "kombistek"
    Other = "other"


class User(ormar.Model):
    class Meta(BaseMeta):
        tablename = "users"

    npm: int = ormar.Integer(primary_key=True)
    username: str = ormar.String(max_length=128)
    name: str = ormar.String(max_length=256, nullable=True)
    is_admin: bool = ormar.Boolean(default=False)

    if TYPE_CHECKING:
        courses_taken: QuerysetProxy["Course"]
        courses_owned: QuerysetProxy["Course"]


class Course(ormar.Model):
    class Meta(BaseMeta):
        tablename = "courses"

    id: ormar.UUID = ormar.UUID(primary_key=True, default=uuid.uuid4)
    name: str = ormar.String(max_length=100)
    matkul: str = ormar.String(max_length=25, choices=list(Subject))
    datetime: dt = ormar.DateTime(name="datetime", timezone=True)
    link: str = ormar.Text(nullable=True)
    students_limit = ormar.Integer(nullable=True)
    notes: str = ormar.Text(nullable=True)
    notes_short: str = ormar.String(max_length=100, nullable=True)
    hidden: bool = ormar.Boolean(default=False)

    teacher = ormar.ForeignKey(User, related_name="courses_owned", nullable=False)
    students = ormar.ManyToMany(User, related_name="courses_taken")
