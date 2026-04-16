from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from src.leorent_backend.schemas.photo import UploadPhotoRequest, UploadPhotoResponse
from src.leorent_backend.services.backblaze_service import backblaze_service
from io import BytesIO

photo_router = APIRouter(prefix="/photos", tags=["photos"])


@photo_router.post("/upload-from-url", response_model=UploadPhotoResponse)
async def upload_photo_from_url(request: UploadPhotoRequest):
    try:
        url = await backblaze_service.upload_photo_from_url(
            photo_url=str(request.photo_url),
            s3_key=request.file_key
        )
        return UploadPhotoResponse(success=True, public_url=url)
    except Exception as e:
        return UploadPhotoResponse(
            success=False, public_url=None, error=str(e))


@photo_router.post("/upload-from-file", response_model=UploadPhotoResponse)
async def upload_photo_from_file(
    file_key: str,
    file: UploadFile = File(...)
):
    """Upload local file content to Backblaze"""
    try:
        file_bytes = await file.read()
        content_type = file.content_type or "application/octet-stream"

        url = await backblaze_service.upload_photo_from_bytes(
            data=file_bytes,
            s3_key=file_key,
            content_type=content_type,
        )

        return UploadPhotoResponse(success=True, public_url=url)
    except Exception as e:
        return UploadPhotoResponse(
            success=False, public_url=None, error=str(e))


@photo_router.get("/download/{file_key:path}")
async def download_photo(file_key: str):
    """Скачати фото з Backblaze"""
    from loguru import logger

    logger.info(f"Запит на скачування: {file_key}")
    photo_bytes = await backblaze_service.download_photo(file_key)

    if photo_bytes is None:
        logger.warning(f"Фото не знайдено: {file_key}")
        raise HTTPException(status_code=404, detail="Фото не знайдено")

    logger.info(f"Повертаю фото: {file_key}, розмір: {len(photo_bytes)} байт")
    return StreamingResponse(
        BytesIO(photo_bytes),
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"attachment; filename={file_key.split('/')[-1]}"}
    )


@photo_router.delete("/delete/{file_key:path}")
async def delete_photo(file_key: str):
    """Видалити фото з Backblaze"""
    success = await backblaze_service.delete_photo(file_key)

    if not success:
        raise HTTPException(status_code=500, detail="Не вдалось видалити фото")

    return {
        "success": True,
        "message": f"Фото успішно видалено: {file_key}"
    }
