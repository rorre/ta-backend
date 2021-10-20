from datetime import timedelta, timezone
import httpx

from ta_backend.models import Course, Subject

jkt_timezone = timezone(timedelta(hours=7))
description_fmt = "Course Name: {}\nTeacher: {}\nMatkul: {}\nDatetime: {}\nStudent Limit: {}\n\nCourse Code:```{}```"


def generate_webhook(course: Course):
    data = {"embeds": [{"title": "New Course!", "description": ""}]}
    data["embeds"][0]["description"] = description_fmt.format(
        course.name,
        course.teacher.name,
        Subject(course.matkul).name,
        course.datetime.astimezone(jkt_timezone).strftime("%Y-%m-%dT%H:%M:%S"),
        str(course.students_limit) if course.students_limit else "Infinity",
        str(course.id),
    )
    return data


async def send_webhook(webhook_url: str, course: Course):
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=generate_webhook(course))
