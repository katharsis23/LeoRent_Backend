from contextlib import asynccontextmanager

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis import asyncio as aioredis


class RedisSettings(BaseSettings):
    redis_url: SecretStr = Field(
        alias="REDIS_URL",
        default=SecretStr("redis://localhost:6379/0"),
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


REDIS_CONFIG = RedisSettings()


redis_client = aioredis.from_url(
    REDIS_CONFIG.redis_url.get_secret_value(),
    decode_responses=True,
    health_check_interval=30,
    encoding="utf-8",
)


@asynccontextmanager
async def redis_session():
    try:
        yield redis_client
    except Exception as e:
        raise e
