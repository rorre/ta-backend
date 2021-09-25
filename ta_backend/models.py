import uuid
from datetime import datetime
from enum import Enum

import ormar

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
    # courses: t.Optional[t.List[Course]]


class Course(ormar.Model):
    class Meta(BaseMeta):
        tablename = "courses"

    id: ormar.UUID = ormar.UUID(primary_key=True, default=uuid.uuid4)
    name: str = ormar.String(max_length=100)
    matkul: str = ormar.String(max_length=25, choices=list(Subject))
    datetime_: datetime = ormar.DateTime(name="datetime", timezone=True)
    link: str = ormar.Text(nullable=True)
    students_limit = ormar.Integer(nullable=True)
    notes: str = ormar.Text(nullable=True)

    teacher = ormar.ForeignKey(User, related_name="courses_owned")
    students = ormar.ManyToMany(User, related_name="courses_taken")
