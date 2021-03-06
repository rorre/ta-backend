from black import traceback
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ta_backend.helper.settings import settings
from ta_backend.models import User
from ta_backend.plugins import manager
from ta_backend.sso.client import AuthError, UIClient

router = APIRouter(prefix="/auth")
client = UIClient(f"http://{settings.hostname}/auth/callback")


@router.get("/login")
def login():
    return RedirectResponse(client.login_url)


@router.get("/callback")
async def callback(ticket: str = Query(...)):
    try:
        sso_response = await client.authenticate(ticket)
    except AuthError:
        return {"err": "Authentication failure. Please try again."}
    except Exception:
        traceback.print_exc()
        return {"err": "An error has occured."}

    kd = sso_response["attributes"]["kd_attributes"]
    if kd and kd["faculty"] != "ILMU KOMPUTER":
        raise HTTPException(
            status_code=401,
            detail="This service is only available for Faculty of Computer Science students.",
        )

    user = await User.objects.get_or_create(
        npm=sso_response["attributes"]["npm"],
        username=sso_response["username"].lower(),
    )
    await user.update(name=sso_response["attributes"]["nama"])

    response = HTMLResponse(
        content="""<script>window.opener.postMessage("logged", "*")</script>"""
    )
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


@router.get("/logout")
async def logout(user: User = Depends(manager)):
    response = JSONResponse(content={"message": "Logged out."})
    response.set_cookie("access-token")
    return response
