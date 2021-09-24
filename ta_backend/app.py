import typing as t

from fastapi import Depends, FastAPI

from ta_backend.helper.database import database
from ta_backend.models import Course, User
from ta_backend.plugins import manager
from ta_backend.routes.auth import router as AuthRouter

app = FastAPI()
app.include_router(AuthRouter)


@app.get("/")
async def root():
    return {"message": "Hello world!"}


@app.get("/check")
async def chk(user=Depends(manager)):
    return {"message": f"Hello {user.name}!"}


@app.get("/user", response_model=t.List[User])
async def user():
    return await User.objects.all()


@app.get("/course", response_model=t.List[Course])
async def course():
    x = await Course.objects.select_related("teacher").all()
    print(x)
    return x


@app.on_event("startup")
async def on_startup():
    if not database.is_connected:
        await database.connect()

    # u1 = await User.objects.create(name="Ren", username="ren")
    # u2 = await User.objects.create(name="Ben", username="ben")
    # c = await Course.objects.create(name="asd", matkul="ddp", teacher=u1)
    # await c.students.add(u2)


@app.on_event("shutdown")
async def on_shutdown():
    if database.is_connected:
        await database.disconnect()
