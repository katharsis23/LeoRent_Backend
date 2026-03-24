from pydantic import BaseModel, HttpUrl


class UploadPhotoRequest(BaseModel):
    photo_url: HttpUrl  # URL для скачування
    file_key: str       # Ключ для збереження (папка/назва)


class UploadPhotoResponse(BaseModel):
    success: bool
    public_url: str | None  # Публічний URL у Backblaze
    error: str | None = None
