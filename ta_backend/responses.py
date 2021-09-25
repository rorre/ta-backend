import typing as t
from datetime import datetime

from pydantic import BaseModel


class DefaultResponse(BaseModel):
    message: str


class CourseResponse(BaseModel):
    id: str
    name: str
    matkul: str
    datetime: datetime
    teacher: str
    students_count: int
    students_limit: t.Optional[int]
    is_enrolled: bool


class CourseDetailReponse(CourseResponse):
    link: t.Optional[str]
    notes: t.Optional[str]
