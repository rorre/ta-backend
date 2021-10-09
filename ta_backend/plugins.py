import aioredis
from datetime import timedelta

from fastapi_login import LoginManager

from ta_backend.helper.settings import settings
from ta_backend.models import User

manager = LoginManager(
    settings.secret,
    "/auth/login",
    use_cookie=True,
    use_header=False,
    default_expiry=timedelta(hours=24),
)
redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


@manager.user_loader()  # type: ignore
async def get_user(identifier):
    return await User.objects.select_related("courses_taken").get_or_none(**identifier)
