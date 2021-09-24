import json
import os
import typing as t
import urllib.parse
from turtle import st

import httpx
import xmltodict

path = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(path, "additional-info.json")

with open(filename, "r") as f:
    additional_datas: t.Dict = json.load(f)


class Attributes(t.TypedDict):
    ldap_cn: str
    kd_org: str
    peran_user: str
    nama: str
    npm: str


class SuccessResponse(t.TypedDict):
    user: str
    attributes: Attributes


FailureResponse = t.TypedDict(
    "FailureResponse",
    {
        "@code": str,
        "#text": str,
    },
)


class Response(t.TypedDict):
    authenticationSuccess: SuccessResponse
    authenticationFailure: FailureResponse


class User(t.TypedDict):
    username: str
    attributes: Attributes


def _normalize_keys(resp: t.Dict):
    new_dict = {}
    for k in resp:
        new_k = k
        if k.startswith("cas:"):
            new_k = k[4:]

        if isinstance(resp[k], dict):
            new_dict[new_k] = _normalize_keys(resp[k])
        else:
            new_dict[new_k] = resp[k]
    return new_dict


class UIClient:
    SSO_URL = "https://sso.ui.ac.id/cas2"

    def __init__(self, service_url):
        parsed_url = urllib.parse.quote_plus(service_url)

        self.service_url = service_url
        self.login_url = self.SSO_URL + "/login?service=" + parsed_url
        self.auth_url = self.SSO_URL + f"/serviceValidate?service={parsed_url}&ticket="

    def get_logout_url(self, redirect_url: t.Optional[str] = None):
        logout_url = self.SSO_URL + "/logout"
        if redirect_url:
            logout_url += "?url=" + urllib.parse.quote_plus(redirect_url)
        return logout_url

    async def authenticate(self, ticket: str) -> User:
        async with httpx.AsyncClient() as client:
            r = await client.get(self.auth_url + ticket)

        output = xmltodict.parse(r.text)
        normalized: Response = _normalize_keys(output["cas:serviceResponse"])
        if "authenticationSuccess" in normalized:
            user = normalized["authenticationSuccess"]
            user["attributes"].update(
                additional_datas.get(user["attributes"]["kd_org"], {})
            )
            return {
                "username": user["user"],
                "attributes": user["attributes"],
            }
        else:
            raise Exception(
                "Error from server: " + normalized["authenticationFailure"]["#text"]
            )
