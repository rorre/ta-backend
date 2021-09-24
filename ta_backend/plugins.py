from fastapi_login import LoginManager

from ta_backend.helper.settings import settings
from ta_backend.models import User

manager = LoginManager(settings.secret, "/login", use_cookie=True)


@manager.user_loader()  # type: ignore
async def get_user(identifier):
    return await User.objects.get_or_none(**identifier)
