import re
import typing as t
import urllib.parse
from datetime import datetime, timedelta, timezone
from uuid import UUID

import ujson
import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel

from ta_backend.models import Course, Subject, User
from ta_backend.plugins import manager, redis
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


def _is_invite_url(url: str) -> bool:
    ZOOM_RE = re.compile(r"\/j\/\d+")
    GMEET_RE = re.compile(r"\/\w{3}-\w{4}-\w{3}")

    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "zoom.us":
        return bool(ZOOM_RE.search(parsed.path))
    elif parsed.netloc == "meet.google.com":
        return bool(GMEET_RE.search(parsed.path))

    return False


def _current_dt_aware():
    return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(jkt_timezone)


async def _create_coursedict(course: Course, user: User, include_students=False):
    response = course.dict(exclude={"datetime", "matkul", "teacher", "students"})
    if include_students:
        student_count = len(course.students)
    else:
        student_count: int = await course.students.count()  # type: ignore

    response.update(
        {
            "id": str(course.id),
            "matkul": Subject(course.matkul).name,
            "datetime": course.datetime.astimezone(jkt_timezone).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            "teacher": course.teacher.name,
            "teacher_npm": course.teacher.npm,
            "students_count": student_count,
            "is_enrolled": course in user.courses_taken or user.is_admin,
        }
    )
    if include_students:
        response.update(
            {
                "students": [s.name for s in course.students],
            }
        )
    return response


@router.get(
    "/list",
    response_model=t.List[CourseResponse],
    dependencies=[
        Depends(RateLimiter(times=300, minutes=1)),
    ],
)
async def courses_list(user: User = Depends(manager), page: int = Query(1)):
    courses = (
        await Course.objects.paginate(page, 10)
        .order_by("-datetime")
        .select_related("teacher")
        .all()
    )
    response = []
    for c in courses:
        response.append(await _create_coursedict(c, user))
    return response


@router.get("/available", response_model=t.List[CourseResponse])
async def courses_available(user: User = Depends(manager), page: int = Query(1)):
    current_time = _current_dt_aware()

    # Let admin see hidden courses
    filters = Course.datetime >= current_time
    if not user.is_admin:
        filters &= Course.hidden == False  # noqa

    courses = (
        await Course.objects.filter(filters)
        .paginate(page, 10)
        .order_by("-datetime")
        .select_related("teacher")
        .all()
    )
    response = []
    for c in courses:
        response.append(await _create_coursedict(c, user))
    return response


@router.get(
    "/mine",
    response_model=t.List[CourseResponse],
    dependencies=[
        Depends(RateLimiter(times=300, minutes=1)),
    ],
)
async def courses_mine(user: User = Depends(manager), page: int = Query(1)):
    courses = (
        await Course.objects.filter(Course.teacher.npm == user.npm)
        .paginate(page, 10)
        .order_by("-datetime")
        .all()
    )
    response = []
    for c in courses:
        response.append(await _create_coursedict(c, user))
    return response


@router.get(
    "/enrolled",
    response_model=t.List[CourseResponse],
    dependencies=[
        Depends(RateLimiter(times=300, minutes=1)),
    ],
)
async def courses_enrolled(user: User = Depends(manager), page: int = Query(1)):
    courses = (
        await user.courses_taken.select_related("teacher")
        .paginate(page, 10)
        .order_by("-datetime")
        .all()
    )
    response = []
    for c in courses:
        response.append(await _create_coursedict(c, user))
    return response


@router.post(
    "/create",
    response_model=CourseResponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=3)),
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

    if course.link and not _is_invite_url(course.link):
        raise HTTPException(status_code=400, detail="Invalid Meet/Zoom URL.")

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
    return await _create_coursedict(c, user)


@router.post(
    "/{course_id}/enroll",
    response_model=DefaultResponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=1)),
    ],
)
async def course_enroll(course_id: UUID, user: User = Depends(manager)):
    redis_key = f"{str(course_id)}--detail"

    c = await Course.objects.select_related("teacher").get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if c.teacher == user:
        raise HTTPException(
            status_code=403, detail="You cannot enroll to your own course."
        )

    # Reset tzinfo to None again because c.datetime is not timezone aware
    # for no reason
    current_time = _current_dt_aware().replace(tzinfo=pytz.utc) - timedelta(hours=7)
    if current_time > c.datetime:
        raise HTTPException(status_code=403, detail="Course has already started!")
    if c.students_limit and (await c.students.count()) >= c.students_limit:  # type: ignore
        raise HTTPException(status_code=403, detail="Course is already full.")

    await c.students.add(user)
    await redis.delete(redis_key)
    return {"message": "Successfully enrolled!"}


@router.post(
    "/{course_id}/unenroll",
    response_model=DefaultResponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=1)),
    ],
)
async def course_unenroll(course_id: UUID, user: User = Depends(manager)):
    redis_key = f"{str(course_id)}--detail"

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
    await redis.delete(redis_key)
    return {"message": "Unenrolled from course."}


@router.get(
    "/{course_id}/detail",
    response_model=CourseDetailReponse,
    dependencies=[Depends(RateLimiter(times=20, seconds=1))],
)
async def course_detail(course_id: UUID, user: User = Depends(manager)):
    redis_key = f"{str(course_id)}--detail"

    # Try to figure out if current used is a student or teacher
    # WITHOUT calling database, as we already have the data from
    # user.
    is_student = False
    is_teacher = False

    course: Course
    for course in user.courses_taken:
        if course.id == course_id:
            is_student = True
            break

    for course in user.courses_owned:
        if course.id == course_id:
            is_teacher = True
            break

    can_fetch = is_student or is_teacher or user.is_admin
    if not can_fetch:
        raise HTTPException(
            status_code=401, detail="You are not enrolled to this course."
        )

    # Search if cache exist in redis
    course_dict: str = await redis.get(redis_key)
    if course_dict:
        return ujson.loads(course_dict)

    c = await Course.objects.select_all().get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")

    course_dict = await _create_coursedict(c, user, include_students=True)
    await redis.set(redis_key, ujson.dumps(course_dict))
    return course_dict


@router.post(
    "/{course_id}/update",
    response_model=CourseDetailReponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=3)),
    ],
)
async def course_update(
    course_id: UUID,
    course_data: CourseCreate,
    user: User = Depends(manager),
):
    redis_key = f"{str(course_id)}--detail"
    current_time = _current_dt_aware()

    if course_data.link and not _is_invite_url(course_data.link):
        raise HTTPException(status_code=400, detail="Invalid Meet/Zoom URL.")

    c = await Course.objects.select_related("teacher").get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if user != c.teacher and not user.is_admin:
        raise HTTPException(status_code=401, detail="You are not allowed to do this.")

    is_dt_changed = c.datetime != course_data.datetime
    if is_dt_changed:
        if c.datetime < course_data.datetime:
            raise HTTPException(status_code=400, detail="You cannot reopen a class.")

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

    if course_data.students_limit and course_data.students_limit <= 0:
        course_data.students_limit = None
    await c.update(**course_data.dict())
    await redis.delete(redis_key)
    return await _create_coursedict(c, user)


@router.delete(
    "/{course_id}/delete",
    response_model=DefaultResponse,
    dependencies=[
        Depends(RateLimiter(times=1, seconds=10)),
    ],
)
async def course_delete(course_id: UUID, user: User = Depends(manager)):
    redis_key = f"{str(course_id)}--detail"

    c = await Course.objects.select_related("teacher").get_or_none(id=course_id)
    if not c:
        raise HTTPException(status_code=404, detail="Course not found!")
    if user != c.teacher and not user.is_admin:
        raise HTTPException(status_code=401, detail="You are not allowed to do this.")
    await c.delete()

    await redis.delete(redis_key)
    return {"message": "Course deleted."}
