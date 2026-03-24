"""
Тести для фото сервісу (Backblaze)
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.leorent_backend.main import app


@pytest.fixture
def client():
    """Test client для фото ендпоїнтів"""
    return TestClient(app)


class TestPhotoUpload:
    """Тести для завантаження фото"""
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.upload_photo_from_url")
    def test_upload_photo_success(self, mock_upload, client):
        """Тест успішного завантаження фото"""
        # Мокуємо успішне завантаження
        mock_upload.return_value = "https://s3.eu-central-003.backblazeb2.com/leorent-photos/users/123/avatar.jpg"
        
        response = client.post(
            "/photos/upload-from-url",
            json={
                "photo_url": "https://via.placeholder.com/150",
                "file_key": "users/123/avatar.jpg"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["public_url"] == "https://s3.eu-central-003.backblazeb2.com/leorent-photos/users/123/avatar.jpg"
        assert data["error"] is None
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.upload_photo_from_url")
    def test_upload_photo_failure(self, mock_upload, client):
        """Тест помилки при завантаженні фото"""
        # Мокуємо помилку
        mock_upload.side_effect = Exception("Network error")
        
        response = client.post(
            "/photos/upload-from-url",
            json={
                "photo_url": "https://invalid-url.com/photo.jpg",
                "file_key": "users/123/avatar.jpg"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["public_url"] is None
        assert "Network error" in data["error"]
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.upload_photo_from_url")
    def test_upload_photo_invalid_url(self, mock_upload, client):
        """Тест з невалідним URL"""
        response = client.post(
            "/photos/upload-from-url",
            json={
                "photo_url": "not-a-url",
                "file_key": "users/123/avatar.jpg"
            }
        )
        
        # Pydantic валідує URL
        assert response.status_code == 422
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.upload_photo_from_url")
    def test_upload_photo_missing_file_key(self, mock_upload, client):
        """Тест без обов'язкового поля file_key"""
        response = client.post(
            "/photos/upload-from-url",
            json={
                "photo_url": "https://via.placeholder.com/150"
            }
        )
        
        assert response.status_code == 422

    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.upload_photo_from_bytes")
    def test_upload_photo_from_file_success(self, mock_upload, client):
        """Тест успішного завантаження локального файлу"""
        mock_upload.return_value = "https://s3.eu-central-003.backblazeb2.com/leorent-photos/som.png"

        file_content = b"fake file"
        response = client.post(
            "/photos/upload-from-file?file_key=som.png",
            files={"file": ("som.png", file_content, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["public_url"] == "https://s3.eu-central-003.backblazeb2.com/leorent-photos/som.png"
        assert data["error"] is None

    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.upload_photo_from_bytes")
    def test_upload_photo_from_file_failure(self, mock_upload, client):
        """Тест помилки при завантаженні локального файлу"""
        mock_upload.side_effect = Exception("Upload error")

        file_content = b"fake file"
        response = client.post(
            "/photos/upload-from-file?file_key=som.png",
            files={"file": ("som.png", file_content, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["public_url"] is None
        assert "Upload error" in data["error"]


class TestPhotoDownload:
    """Тести для скачування фото"""
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.download_photo")
    async def test_download_photo_success(self, mock_download, client):
        """Тест успішного скачування фото"""
        # Мокуємо фото
        photo_bytes = b"fake photo data"
        mock_download.return_value = photo_bytes
        
        response = client.get("/photos/download/users/123/avatar.jpg")
        
        assert response.status_code == 200
        assert response.content == photo_bytes
        assert "image/jpeg" in response.headers.get("content-type", "")
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.download_photo")
    async def test_download_photo_not_found(self, mock_download, client):
        """Тест коли фото не знайдено"""
        # Мокуємо None (фото не існує)
        mock_download.return_value = None
        
        response = client.get("/photos/download/users/999/nonexistent.jpg")
        
        assert response.status_code == 404
        detail = response.json()["detail"].lower()
        assert "фото" in detail or "not found" in detail
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.download_photo")
    async def test_download_photo_with_spaces(self, mock_download, client):
        """Тест скачування файлу з пробілами в імені"""
        # Мокуємо фото
        photo_bytes = b"fake photo data"
        mock_download.return_value = photo_bytes
        
        response = client.get("/photos/download/Screenshot%20from%202026-02-17%2012-14-56.png")
        
        assert response.status_code == 200
        assert response.content == photo_bytes
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.download_photo")
    async def test_download_photo_with_nested_path(self, mock_download, client):
        """Тест скачування з вкладеними папками"""
        photo_bytes = b"fake photo data"
        mock_download.return_value = photo_bytes
        
        response = client.get("/photos/download/apartments/456/living-room/photo-1.jpg")
        
        assert response.status_code == 200
        assert response.content == photo_bytes
        # Перевіри що file_key передано правильно
        mock_download.assert_called_once_with("apartments/456/living-room/photo-1.jpg")


class TestPhotoDelete:
    """Тести для видалення фото"""
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.delete_photo")
    async def test_delete_photo_success(self, mock_delete, client):
        """Тест успішного видалення фото"""
        # Мокуємо успішне видалення
        mock_delete.return_value = True
        
        response = client.delete("/photos/delete/users/123/avatar.jpg")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully" in data["message"].lower() or "успішно" in data["message"].lower()
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.delete_photo")
    async def test_delete_photo_failure(self, mock_delete, client):
        """Тест помилки при видаленні фото"""
        # Мокуємо помилку
        mock_delete.return_value = False
        
        response = client.delete("/photos/delete/users/999/nonexistent.jpg")
        
        assert response.status_code == 500
        assert "не вдалось" in response.json()["detail"].lower() or "fail" in response.json()["detail"].lower()
    
    @patch("src.leorent_backend.services.backblaze_service.backblaze_service.delete_photo")
    async def test_delete_photo_with_spaces(self, mock_delete, client):
        """Тест видалення файлу з пробілами в імені"""
        mock_delete.return_value = True
        
        response = client.delete("/photos/delete/Screenshot%20from%202026-02-17%2012-14-56.png")
        
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestBackblazeServiceUnit:
    """Unit тести для BackblazeService"""
    
    @pytest.mark.asyncio
    @patch("boto3.client")
    @patch("httpx.AsyncClient")
    async def test_upload_photo_from_url_unit(self, mock_http_client, mock_s3_client):
        """Unit тест для upload_photo_from_url"""
        from src.leorent_backend.services.backblaze_service import BackblazeService
        
        # Мокуємо httpx response
        mock_response = AsyncMock()
        mock_response.content = b"fake photo data"
        mock_response.headers.get.return_value = "image/jpeg"
        
        mock_http_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # Мокуємо S3 client
        mock_s3 = MagicMock()
        mock_s3_client.return_value = mock_s3
        
        service = BackblazeService()
        
        result = await service.upload_photo_from_url(
            photo_url="https://via.placeholder.com/150",
            s3_key="test/photo.jpg"
        )
        
        assert result is not None
        assert "test/photo.jpg" in result
        mock_s3.put_object.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_download_photo_unit(self, mock_s3_client):
        """Unit тест для download_photo"""
        from src.leorent_backend.services.backblaze_service import BackblazeService
        
        # Мокуємо S3 client
        mock_s3 = MagicMock()
        mock_response_body = MagicMock()
        mock_response_body.read.return_value = b"fake photo data"
        mock_s3.get_object.return_value = {"Body": mock_response_body}
        mock_s3_client.return_value = mock_s3
        
        service = BackblazeService()
        
        result = await service.download_photo("test/photo.jpg")
        
        assert result == b"fake photo data"
        mock_s3.get_object.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_download_photo_not_found_unit(self, mock_s3_client):
        """Unit тест коли фото не знайдено"""
        from src.leorent_backend.services.backblaze_service import BackblazeService
        from botocore.exceptions import ClientError
        
        # Мокуємо помилку 404
        mock_s3 = MagicMock()
        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_s3.get_object.side_effect = ClientError(error_response, "GetObject")
        mock_s3_client.return_value = mock_s3
        
        service = BackblazeService()
        result = await service.download_photo("nonexistent/photo.jpg")
        
        assert result is None

    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_upload_photo_from_bytes_unit(self, mock_s3_client):
        """Unit тест для upload_photo_from_bytes"""
        from src.leorent_backend.services.backblaze_service import BackblazeService

        mock_s3 = MagicMock()
        mock_s3_client.return_value = mock_s3

        service = BackblazeService()
        result = await service.upload_photo_from_bytes(
            data=b"fake data",
            s3_key="test/som.png",
            content_type="image/png"
        )

        assert "test/som.png" in result
        mock_s3.put_object.assert_called_once()

    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_delete_photo_unit(self, mock_s3_client):
        """Unit тест коли фото не знайдено"""
        from src.leorent_backend.services.backblaze_service import BackblazeService
        from botocore.exceptions import ClientError
        
        # Мокуємо помилку 404
        mock_s3 = MagicMock()
        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_s3.get_object.side_effect = ClientError(error_response, "GetObject")
        mock_s3_client.return_value = mock_s3
        
        service = BackblazeService()
        
        result = await service.download_photo("nonexistent/photo.jpg")
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_delete_photo_unit(self, mock_s3_client):
        """Unit тест для delete_photo"""
        from src.leorent_backend.services.backblaze_service import BackblazeService

        # Мокуємо S3 client
        mock_s3 = MagicMock()
        mock_s3.list_object_versions.return_value = {
            "Versions": [{"Key": "test/photo.jpg", "VersionId": "v1"}],
            "DeleteMarkers": []
        }
        mock_s3_client.return_value = mock_s3

        service = BackblazeService()

        result = await service.delete_photo("test/photo.jpg")

        assert result is True
        mock_s3.delete_object.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("boto3.client")
    async def test_delete_photo_error_unit(self, mock_s3_client):
        """Unit тест видалення коли помилка"""
        from src.leorent_backend.services.backblaze_service import BackblazeService
        from botocore.exceptions import ClientError
        
        # Мокуємо помилку
        mock_s3 = MagicMock()
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_s3.delete_object.side_effect = ClientError(error_response, "DeleteObject")
        mock_s3_client.return_value = mock_s3
        
        service = BackblazeService()
        
        result = await service.delete_photo("test/photo.jpg")
        
        assert result is False
