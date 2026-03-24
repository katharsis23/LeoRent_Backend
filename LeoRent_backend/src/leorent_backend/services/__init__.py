"""
Сервіс для роботи з Backblaze S3
Завантаження та скачування фото
"""

import boto3
from botocore.exceptions import ClientError
from loguru import logger
from typing import Optional
import httpx
from src.leorent_backend.config.backblaze import BACKBLAZE_CONFIG


class BackblazeService:
    """Сервіс для роботи з Backblaze S3 сховищем"""

    def __init__(self):
        """Ініціалізація S3 клієнта"""
        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=BACKBLAZE_CONFIG.endpoint_url,
            aws_access_key_id=BACKBLAZE_CONFIG.access_key,
            aws_secret_access_key=BACKBLAZE_CONFIG.secret_key,
            region_name=BACKBLAZE_CONFIG.region_name,
        )
        self.bucket_name = BACKBLAZE_CONFIG.bucket_name

    async def upload_photo_from_url(
        self,
        photo_url: str,
        s3_key: str,
        timeout: int = 30
    ) -> Optional[str]:
        """
        Завантажити фото з URL в Backblaze

        Args:
            photo_url: URL фото для скачування
            s3_key: Ключ (папка/назва) для збереження в S3
            timeout: Таймаут для скачування (сек)

        Returns:
            URL фото в Backblaze або None при помилці
        """
        try:
            logger.info(f"Завантаження фото з {photo_url}")

            # Скачуємо фото через httpx
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(photo_url)
                response.raise_for_status()
                photo_bytes = response.content

            # Завантажуємо в Backblaze
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=photo_bytes,
                ContentType=response.headers.get("content-type", "image/jpeg")
            )

            logger.info(f"Фото успішно завантажено: {s3_key}")

            # Повертаємо URL фото
            return self._get_photo_url(s3_key)

        except httpx.RequestError as e:
            logger.error(f"Помилка при скачуванні з URL: {e}")
            return None
        except ClientError as e:
            logger.error(f"Помилка Backblaze: {e}")
            return None
        except Exception as e:
            logger.error(f"Невідома помилка при завантаженні: {e}")
            return None

    async def download_photo(
        self,
        s3_key: str
    ) -> Optional[bytes]:
        """
        Скачати фото з Backblaze

        Args:
            s3_key: Ключ фото в S3

        Returns:
            Байти фото або None при помилці
        """
        try:
            logger.info(f"Скачування фото: {s3_key}")

            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            photo_bytes = response["Body"].read()
            logger.info(f"Фото успішно скачано: {s3_key}")

            return photo_bytes

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"Фото не знайдено: {s3_key}")
            else:
                logger.error(f"Помилка Backblaze: {e}")
            return None
        except Exception as e:
            logger.error(f"Невідома помилка при скачуванні: {e}")
            return None

    async def delete_photo(self, s3_key: str) -> bool:
        """
        Видалити фото з Backblaze

        Args:
            s3_key: Ключ фото в S3

        Returns:
            True якщо успішно видалено, False при помилці
        """
        try:
            logger.info(f"Видалення фото: {s3_key}")

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            logger.info(f"Фото успішно видалено: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Помилка Backblaze: {e}")
            return False
        except Exception as e:
            logger.error(f"Невідома помилка при видаленні: {e}")
            return False

    def _get_photo_url(self, s3_key: str) -> str:
        """
        Сформувати публічний URL до фото

        Args:
            s3_key: Ключ фото в S3

        Returns:
            Публічний URL фото
        """
        return f"{BACKBLAZE_CONFIG.endpoint_url}/{self.bucket_name}/{s3_key}"

    async def list_photos(self, prefix: str = "") -> list[str]:
        """
        Отримати список фото в S3

        Args:
            prefix: Префікс для фільтрування (папка)

        Returns:
            Список ключів фото у S3
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if "Contents" not in response:
                return []

            return [obj["Key"] for obj in response["Contents"]]

        except ClientError as e:
            logger.error(f"Помилка при отриманні списку: {e}")
            return []


# Глобальний екземпляр сервісу
backblaze_service = BackblazeService()
