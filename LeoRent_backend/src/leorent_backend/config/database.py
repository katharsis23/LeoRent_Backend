from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr


class DatabaseSettings(BaseSettings):
    database_url: SecretStr = Field(alias="DATABASE_URL")

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


DATABASE_CONFIG = DatabaseSettings()
