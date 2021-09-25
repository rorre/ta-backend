import typing as t
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ta_backend.models import Course, User
from ta_backend.plugins import manager
from ta_backend.responses import CourseDetailReponse, CourseResponse, DefaultResponse


class CourseCreate(BaseModel):
    name: str
    matkul: str
    datetime_: datetime
    students_limit: t.Optional[int]
    notes: t.Optional[str]
    link: t.Optional[str]


router = APIRouter(prefix="/course", dependencies=[Depends(manager)])


def _create_coursedict(course: Course, user: User):
    return {
        "id": str(course.id),
        "name": course.name,
        "matkul": course.matkul,
        "datetime": course.datetime_,
        "teacher": course.teacher.name,
        "students_limit": course.students_limit,
        "students_count": len(course.students),
        "is_enrolled": course.id in user.courses_taken,
    }


@router.get("/list", response_model=t.List[CourseResponse])
async def courses_list(user: User = Depends(manager)):
    courses = await Course.objects.paginate(20).select_related("teacher").all()
    response = []
    for c in courses:
        response.append(_create_coursedict(c, user))
    return response


@router.post("/create", response_model=CourseResponse)
async def course_create(course: CourseCreate, user: User = Depends(manager)):
    c = await Course.objects.create(**course.dict())
    await c.update(teacher=user)
    return _create_coursedict(c, user)


@router.get("/{course_id}/enroll", response_model=DefaultResponse)
async def course_enroll(course_id: UUID, user: User = Depends(manager)):
    c = await Course.objects.get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if c.teacher == user:
        raise HTTPException(
            status_code=403, detail="You cannot enroll to your own course."
        )

    current_time = datetime.utcnow()
    if current_time > c.datetime_:
        raise HTTPException(status_code=403, detail="Course has already started!")
    if len(c.students) >= c.students_limit:
        raise HTTPException(status_code=403, detail="Course is already full.")

    await c.students.add(user)
    return {"message": "Successfully enrolled!"}


@router.get("/{course_id}/detail", response_model=CourseDetailReponse)
async def course_detail(course_id: UUID, user: User = Depends(manager)):
    c = await Course.objects.select_related("teacher").get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if not (user in c.students or user == c.teacher):
        raise HTTPException(
            status_code=401, detail="You are not enrolled to this course."
        )

    course_dict = _create_coursedict(c, user)
    course_dict.update(
        {
            "link": c.link,
            "notes": c.notes,
        }
    )
    return course_dict


@router.post("/{course_id}/update", response_model=CourseDetailReponse)
async def course_update(
    course_id: UUID,
    course_data: CourseCreate,
    user: User = Depends(manager),
):
    c = await Course.objects.select_related("teacher").get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if user != c.teacher:
        raise HTTPException(status_code=401, detail="You are not allowed to do this.")
    await c.update(**course_data.dict())
    return _create_coursedict(c, user)
