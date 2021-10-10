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
    teacher_npm: int
    students_count: int
    students_limit: t.Optional[int]
    is_enrolled: bool
    notes_short: t.Optional[str]
    hidden: bool


class CourseDetailReponse(CourseResponse):
    link: t.Optional[str]
    notes: t.Optional[str]
    students: t.List[str]


class UserResponse(BaseModel):
    npm: int
    username: str
    name: str
    is_admin: bool
