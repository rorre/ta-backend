import json
import os
import typing as t
import urllib.parse

import httpx
import xmltodict

from ta_backend.sso.types import KDAttributes, Response, User


class AuthError(Exception):
    pass


path = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(path, "additional-info.json")

with open(filename, "r") as f:
    additional_datas: t.Dict[str, KDAttributes] = json.load(f)


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
            user["attributes"]["kd_attributes"] = additional_datas.get(
                user["attributes"]["kd_org"]
            )

            return {
                "username": user["user"],
                "attributes": user["attributes"],
            }
        else:
            raise AuthError(
                "Error from server: " + normalized["authenticationFailure"]["#text"]
            )
