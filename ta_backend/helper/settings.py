from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret: str
    hostname: str
    sentry_url: str = ""
    discord_url: str = ""


settings = Settings(".env")
