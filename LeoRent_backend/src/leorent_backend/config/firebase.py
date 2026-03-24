from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Dict, Any, Optional


class FirebaseSettings(BaseSettings):
    type_: Optional[str] = Field(
        default=None,
        alias="FIREBASE_TYPE"
    )
    project_id: Optional[str] = Field(
        default=None,
        alias="FIREBASE_PROJECT_ID"
    )
    private_key_id: Optional[SecretStr] = Field(
        default=None,
        alias="FIREBASE_PRIVATE_KEY_ID"
    )
    private_key: Optional[SecretStr] = Field(
        default=None,
        alias="FIREBASE_PRIVATE_KEY"
    )
    client_email: Optional[str] = Field(
        default=None,
        alias="FIREBASE_CLIENT_EMAIL"
    )
    client_id: Optional[str] = Field(
        default=None,
        alias="FIREBASE_CLIENT_ID"
    )
    auth_uri: Optional[str] = Field(
        default=None,
        alias="FIREBASE_AUTH_URI"
    )
    token_uri: Optional[str] = Field(
        default=None,
        alias="FIREBASE_TOKEN_URI"
    )

    auth_provider_x509_cert_url: Optional[str] = Field(
        default=None,
        alias="FIREBASE_AUTH_PROVIDER_X509_CERT_URL"
    )

    client_x509_cert_url: Optional[str] = Field(
        default=None,
        alias="FIREBASE_CLIENT_X509_CERT_URL"
    )
    universe_domain: Optional[str] = Field(
        default=None,
        alias="FIREBASE_UNIVERSE_DOMAIN"
    )

    @property
    def credentials_dict(self) -> Dict[str, Any]:
        """Pretty wrapper to JSON path format for Firebase credentials."""
        return {
            "type": self.type_,
            "project_id": self.project_id,
            "private_key_id": (
                self.private_key_id.get_secret_value()
                if self.private_key_id else None
            ),
            "private_key": (
                self.private_key.get_secret_value()
                if self.private_key else None
            ),
            "client_email": self.client_email,
            "client_id": self.client_id,
            "auth_uri": self.auth_uri,
            "token_uri": self.token_uri,
            "auth_provider_x509_cert_url": (
                self.auth_provider_x509_cert_url
            ),
            "client_x509_cert_url": self.client_x509_cert_url,
            "universe_domain": self.universe_domain,
        }

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


FIREBASE_CONFIG = FirebaseSettings()
