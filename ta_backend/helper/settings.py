from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret: str
    hostname: str


settings = Settings(".env")
