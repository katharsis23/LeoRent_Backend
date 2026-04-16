"""
Сервіс для роботи з Backblaze S3
Завантаження та скачування фото
"""

import asyncio
import inspect
from typing import Any, Optional

import boto3
import httpx
from botocore.exceptions import ClientError
from loguru import logger

from src.leorent_backend.config.backblaze import BACKBLAZE_CONFIG


class BackblazeService:
    def __init__(self):
        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=BACKBLAZE_CONFIG.endpoint_url,
            aws_access_key_id=BACKBLAZE_CONFIG.access_key,
            aws_secret_access_key=BACKBLAZE_CONFIG.secret_key.get_secret_value(),
            region_name="eu-central-003",
        )
        self.bucket_name = BACKBLAZE_CONFIG.bucket_name

    async def _resolve_maybe_awaitable(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value

    async def _fetch_photo_details(self, photo_url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            verify=False,
            follow_redirects=True,
            timeout=30.0,
        ) as client:
            response = await client.get(photo_url)
            await self._resolve_maybe_awaitable(response.raise_for_status())

            raw_content_type = response.headers.get(
                "content-type", "image/jpeg"
            )
            raw_content_type = await self._resolve_maybe_awaitable(
                raw_content_type
            )
            content_type = str(raw_content_type).split(";")[0].strip().lower()

            if not content_type.startswith("image/"):
                raise ValueError(
                    "URL must point directly to an image, not an HTML page."
                )

            photo_bytes = await self._resolve_maybe_awaitable(response.content)

        return {
            "data": photo_bytes,
            "content_type": content_type,
            "size_bytes": len(photo_bytes),
        }

    async def upload_photo_from_url_details(
        self,
        photo_url: str,
        s3_key: str,
    ) -> dict[str, Any]:
        """Скачати фото за прямим URL і завантажити в Backblaze."""
        photo_details = await self._fetch_photo_details(photo_url)

        await asyncio.to_thread(
            self.s3_client.put_object,
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=photo_details["data"],
            ContentType=photo_details["content_type"],
        )

        return {
            "url": self._get_photo_url(s3_key),
            "content_type": photo_details["content_type"],
            "size_bytes": photo_details["size_bytes"],
        }

    async def upload_photo_from_url(self, photo_url: str, s3_key: str):
        result = await self.upload_photo_from_url_details(photo_url, s3_key)
        return result["url"]

    async def upload_photo_from_source_details(
        self,
        source: str,
        s3_key: str,
    ) -> dict[str, Any]:
        """Upload photo from an existing URL or reuse a Backblaze URL."""
        normalized_source = source.strip()
        base_url = self._get_photo_url("")

        if normalized_source.startswith(base_url):
            photo_details = await self._fetch_photo_details(normalized_source)
            return {
                "url": normalized_source,
                "content_type": photo_details["content_type"],
                "size_bytes": photo_details["size_bytes"],
            }

        if normalized_source.startswith(("http://", "https://")):
            return await self.upload_photo_from_url_details(
                normalized_source,
                s3_key,
            )

        raise ValueError(
            "Picture source must be a direct http(s) image URL or a file upload."
        )

    async def upload_photo_from_source(self, source: str, s3_key: str) -> str:
        result = await self.upload_photo_from_source_details(source, s3_key)
        return result["url"]

    async def download_photo(self, s3_key: str) -> Optional[bytes]:
        """Скачати фото з Backblaze"""
        try:
            logger.info(f"Скачування фото: {s3_key}")

            # Отримати об'єкт з S3 (без блокування event loop)
            response = await asyncio.to_thread(
                self.s3_client.get_object,
                Bucket=self.bucket_name,
                Key=s3_key
            )

            photo_bytes = response["Body"].read()
            logger.info(
                f"Фото успішно скачано: {s3_key}, розмір: {
                    len(photo_bytes)} байт")

            return photo_bytes

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.warning(
                f"Фото не знайдено: {s3_key}, помилка: {error_code}")
            if error_code == "NoSuchKey":
                return None
            else:
                logger.error(f"Помилка Backblaze: {e}")
                return None
        except Exception as e:
            logger.error(f"Невідома помилка при скачуванні {s3_key}: {e}")
            return None

    async def delete_photo(self, s3_key: str) -> bool:
        """Повністю видалити фото з Backblaze (всі версії + delete markers)"""
        try:
            logger.info(f"Повне видалення фото: {s3_key}")

            # Отримати всі версії об'єкта
            response = await asyncio.to_thread(
                self.s3_client.list_object_versions,
                Bucket=self.bucket_name,
                Prefix=s3_key
            )

            deleted_any = False

            # Видалити всі версії файлу
            for version in response.get("Versions", []):
                if version["Key"] == s3_key:
                    await asyncio.to_thread(
                        self.s3_client.delete_object,
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        VersionId=version["VersionId"]
                    )
                    deleted_any = True

            # Видалити всі delete markers
            for marker in response.get("DeleteMarkers", []):
                if marker["Key"] == s3_key:
                    await asyncio.to_thread(
                        self.s3_client.delete_object,
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        VersionId=marker["VersionId"]
                    )
                    deleted_any = True

            if deleted_any:
                logger.info(f"Фото повністю видалено: {s3_key}")
            else:
                logger.warning(f"Фото не знайдено: {s3_key}")

            return deleted_any

        except ClientError as e:
            logger.error(f"Помилка Backblaze при видаленні: {e}")
            return False
        except Exception as e:
            logger.error(f"Невідома помилка при видаленні: {e}")
            return False

    async def upload_photo_from_bytes(
        self,
        data: bytes,
        s3_key: str,
        content_type: str = "image/jpeg"
    ) -> str:
        """Завантажити бінарні дані як файл у Backblaze"""
        await asyncio.to_thread(
            self.s3_client.put_object,
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )
        return self._get_photo_url(s3_key)

    def _get_photo_url(self, s3_key: str) -> str:
        return f"{BACKBLAZE_CONFIG.endpoint_url}/{self.bucket_name}/{s3_key}"


# Глобальний екземпляр сервісу
backblaze_service = BackblazeService()
