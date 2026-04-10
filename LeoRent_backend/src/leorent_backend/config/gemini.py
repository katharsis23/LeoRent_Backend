from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr


class GeminiSettings(BaseSettings):
    api_key: SecretStr = Field(
        default=SecretStr(""),
        alias="GEMINI_API_KEY"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


GEMINI_SETTINGS = GeminiSettings()
