import typing as t


class KDAttributes(t.TypedDict):
    faculty: str
    study_program: str
    educational_program: str


class Attributes(t.TypedDict):
    ldap_cn: str
    kd_org: str
    kd_attributes: t.Optional[KDAttributes]
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


class Response(t.TypedDict, total=False):
    authenticationSuccess: SuccessResponse
    authenticationFailure: FailureResponse


class User(t.TypedDict):
    username: str
    attributes: Attributes
