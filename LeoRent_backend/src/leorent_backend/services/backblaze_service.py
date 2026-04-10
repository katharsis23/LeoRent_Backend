"""
Сервіс для роботи з Backblaze S3
Завантаження та скачування фото
"""

import boto3
import httpx
import asyncio
from loguru import logger
from typing import Optional
from botocore.exceptions import ClientError
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

    async def upload_photo_from_url(self, photo_url: str, s3_key: str):
        # 1. Скачити фото
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(photo_url)
            photo_bytes = response.content

        # 2. Завантажити в S3 (без блокування event loop)
        await asyncio.to_thread(
            self.s3_client.put_object,
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=photo_bytes,
            ContentType="image/jpeg"
        )

        # 3. Повернути URL
        return self._get_photo_url(s3_key)

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
