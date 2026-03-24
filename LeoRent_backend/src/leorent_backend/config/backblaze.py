from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr


class BackblazeSettings(BaseSettings):
    """Backblaze S3 конфіг"""
    access_key: str = Field(
        alias="BACKBLAZE_ACCESS_KEY",
        default=""
    )

    secret_key: SecretStr = Field(
        alias="BACKBLAZE_SECRET_KEY",
        default=SecretStr("")
    )

    bucket_name: str = Field(
        alias="BACKBLAZE_BUCKET_NAME",
        default="leorent-photos"
    )

    endpoint_url: str = Field(
        alias="BACKBLAZE_ENDPOINT_URL",
        default="https://s3.eu-central-003.backblazeb2.com"
    )

    region_name: str = Field(
        default="eu-central-003"
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


BACKBLAZE_CONFIG = BackblazeSettings()
