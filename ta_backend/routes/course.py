import typing as t
from datetime import datetime, timezone, timedelta
from uuid import UUID

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel

from ta_backend.models import Course, Subject, User
from ta_backend.plugins import manager
from ta_backend.responses import CourseDetailReponse, CourseResponse, DefaultResponse

jkt_timezone = timezone(timedelta(hours=7))


class CourseCreate(BaseModel):
    name: str
    matkul: str
    datetime: datetime
    students_limit: t.Optional[int] = None
    notes: t.Optional[str] = ""
    link: t.Optional[str] = ""
    notes_short: t.Optional[str] = ""
    hidden: bool

    def __init__(self, *args, **kwargs):
        dt_str = kwargs.pop("datetime")
        kwargs["datetime"] = datetime.fromisoformat(dt_str).replace(tzinfo=jkt_timezone)
        super().__init__(*args, **kwargs)


router = APIRouter(
    prefix="/course",
    dependencies=[
        Depends(manager),
    ],
)


def _current_dt_aware():
    return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(jkt_timezone)


def _create_coursedict(course: Course, user: User):
    response = course.dict(exclude={"datetime", "matkul", "teacher", "students"})
    response.update(
        {
            "id": str(course.id),
            "matkul": Subject(course.matkul).name,
            "datetime": course.datetime.astimezone(jkt_timezone).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            "teacher": course.teacher.name,
            "teacher_npm": course.teacher.npm,
            "students_count": len(course.students),
            "is_enrolled": course in user.courses_taken,
            "students": [s.name for s in course.students],
        }
    )
    return response


@router.get("/list", response_model=t.List[CourseResponse])
async def courses_list(user: User = Depends(manager), page: int = Query(1)):
    courses = (
        await Course.objects.paginate(page, 10).order_by("-datetime").select_all().all()
    )
    response = []
    for c in courses:
        response.append(_create_coursedict(c, user))
    return response


@router.get("/available", response_model=t.List[CourseResponse])
async def courses_available(user: User = Depends(manager), page: int = Query(1)):
    current_time = _current_dt_aware()
    courses = (
        await Course.objects.filter(
            (Course.datetime >= current_time) & (Course.hidden == False)  # noqa
        )
        .paginate(page, 10)
        .order_by("-datetime")
        .select_all()
        .all()
    )
    response = []
    for c in courses:
        response.append(_create_coursedict(c, user))
    return response


@router.get("/mine", response_model=t.List[CourseResponse])
async def courses_mine(user: User = Depends(manager), page: int = Query(1)):
    courses = (
        await Course.objects.filter(Course.teacher.npm == user.npm)
        .paginate(page, 10)
        .order_by("-datetime")
        .select_all()
        .all()
    )
    response = []
    for c in courses:
        response.append(_create_coursedict(c, user))
    return response


@router.get("/enrolled", response_model=t.List[CourseResponse])
async def courses_enrolled(user: User = Depends(manager), page: int = Query(1)):
    courses = (
        await user.courses_taken.select_all()
        .paginate(page, 10)
        .order_by("-datetime")
        .all()
    )
    response = []
    for c in courses:
        response.append(_create_coursedict(c, user))
    return response


@router.post(
    "/create",
    response_model=CourseResponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=10)),
        Depends(RateLimiter(times=2, seconds=60)),
    ],
)
async def course_create(course: CourseCreate, user: User = Depends(manager)):
    current_time = _current_dt_aware()
    if course.datetime < current_time:
        raise HTTPException(
            status_code=400,
            detail="You cannot pick date and time that happens in the past.",
        )
    elif (course.datetime - current_time) > timedelta(days=28):
        raise HTTPException(
            status_code=400,
            detail="Date and Time must be between now and 30 days from now.",
        )

    upcoming_user_courses = await Course.objects.filter(
        (Course.datetime > current_time) & (Course.teacher.npm == user.npm)
    ).all()
    if len(upcoming_user_courses) >= 2:
        raise HTTPException(
            status_code=400, detail="You can only have at most 2 upcoming classes."
        )

    if course.students_limit and course.students_limit <= 0:
        course.students_limit = None
    c = await Course.objects.create(**course.dict())
    await c.update(teacher=user)
    return _create_coursedict(c, user)


@router.post(
    "/{course_id}/enroll",
    response_model=DefaultResponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=1)),
    ],
)
async def course_enroll(course_id: UUID, user: User = Depends(manager)):
    c = await Course.objects.select_all().get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if c.teacher == user:
        raise HTTPException(
            status_code=403, detail="You cannot enroll to your own course."
        )

    # Reset tzinfo to None again because c.datetime is not timezone aware
    # for no reason
    current_time = _current_dt_aware().replace(tzinfo=pytz.utc)
    if current_time > c.datetime:
        raise HTTPException(status_code=403, detail="Course has already started!")
    if c.students_limit and len(c.students) >= c.students_limit:
        raise HTTPException(status_code=403, detail="Course is already full.")

    await c.students.add(user)
    return {"message": "Successfully enrolled!"}


@router.post(
    "/{course_id}/unenroll",
    response_model=DefaultResponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=1)),
    ],
)
async def course_unenroll(course_id: UUID, user: User = Depends(manager)):
    c = await Course.objects.select_all().get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if c.teacher == user:
        raise HTTPException(
            status_code=403, detail="You cannot unenroll to your own course."
        )
    if user not in c.students:
        raise HTTPException(
            status_code=401, detail="You are not enrolled to this course."
        )

    await c.students.remove(user)
    return {"message": "Unenrolled from course."}


@router.get("/{course_id}/detail", response_model=CourseDetailReponse)
async def course_detail(course_id: UUID, user: User = Depends(manager)):
    c = await Course.objects.select_all().get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if not (user in c.students or user == c.teacher):
        raise HTTPException(
            status_code=401, detail="You are not enrolled to this course."
        )

    course_dict = _create_coursedict(c, user)
    return course_dict


@router.post(
    "/{course_id}/update",
    response_model=CourseDetailReponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=10)),
    ],
)
async def course_update(
    course_id: UUID,
    course_data: CourseCreate,
    user: User = Depends(manager),
):
    current_time = _current_dt_aware()
    if course_data.datetime < current_time:
        raise HTTPException(
            status_code=400,
            detail="You cannot pick date and time that happens in the past.",
        )
    elif (course_data.datetime - current_time) > timedelta(days=28):
        raise HTTPException(
            status_code=400,
            detail="Date and Time must be between now and 30 days from now.",
        )

    c = await Course.objects.select_related("teacher").get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if user != c.teacher:
        raise HTTPException(status_code=401, detail="You are not allowed to do this.")

    time_utc = current_time.replace(tzinfo=pytz.utc)
    if c.datetime < time_utc:
        raise HTTPException(status_code=400, detail="You cannot reopen a class.")

    if course_data.students_limit and course_data.students_limit <= 0:
        course_data.students_limit = None
    await c.update(**course_data.dict())
    return _create_coursedict(c, user)


@router.delete(
    "/{course_id}/delete",
    response_model=DefaultResponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=10)),
    ],
)
async def course_delete(course_id: UUID, user: User = Depends(manager)):
    c = await Course.objects.select_related("teacher").get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if user != c.teacher:
        raise HTTPException(status_code=401, detail="You are not allowed to do this.")
    await c.delete()
    return {"message": "Course deleted."}
