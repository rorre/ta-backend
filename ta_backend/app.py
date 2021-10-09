import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter

from ta_backend.helper.database import database
from ta_backend.helper.settings import settings
from ta_backend.models import User
from ta_backend.plugins import manager, redis
from ta_backend.responses import DefaultResponse
from ta_backend.routes.auth import router as AuthRouter
from ta_backend.routes.course import router as CourseRouter

app = FastAPI()
app.include_router(AuthRouter)
app.include_router(CourseRouter)
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.sentry_url:
    sentry_sdk.init(settings.sentry_url)
    app.add_middleware(SentryAsgiMiddleware)


@app.get("/", response_model=DefaultResponse)
async def root():
    return {"message": "Hello world!"}


@app.get(
    "/me",
    response_model=User,
    response_model_exclude={"courses_owned", "courses_taken"},
)
async def me(user: User = Depends(manager)):
    return user


@app.on_event("startup")
async def on_startup():
    if not database.is_connected:
        await database.connect()

    await FastAPILimiter.init(redis)


@app.on_event("shutdown")
async def on_shutdown():
    if database.is_connected:
        await database.disconnect()
