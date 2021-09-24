from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from ta_backend.helper.settings import settings
from ta_backend.models import User
from ta_backend.plugins import manager
from ta_backend.sso.client import UIClient

router = APIRouter(prefix="/auth")
client = UIClient(f"http://{settings.hostname}/auth/callback")


@router.get("/login")
def login():
    return RedirectResponse(client.login_url)


@router.get("/callback")
async def callback(ticket: str = Query(...)):
    try:
        sso_response = await client.authenticate(ticket)
    except Exception:
        return {"err": "An error has occured."}

    user = await User.objects.get_or_create(
        npm=sso_response["attributes"]["npm"],
        username=sso_response["username"],
    )
    await user.update(name=sso_response["attributes"]["nama"])

    response = RedirectResponse("/")
    token = manager.create_access_token(
        data=dict(
            sub=dict(
                npm=user.npm,
                username=user.username,
            )
        )
    )
    manager.set_cookie(response, token)
    return response
