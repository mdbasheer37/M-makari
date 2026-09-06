"""
Image / thumbnail upload endpoint.
Allows admins to upload images from their phone and get back a URL.
"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from auth_utils import get_current_admin
from media_utils import save_upload
import os

router = APIRouter()

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "application/octet-stream"
}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


def get_base_url() -> str:
    """Return the base URL for constructing media URLs."""
    return os.getenv("RENDER_EXTERNAL_URL", os.getenv("BASE_URL", "https://m-makari.onrender.com"))


@router.post("/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    admin=Depends(get_current_admin),
):
    """
    Upload an image (thumbnail/cover) from the admin's device.
    Returns the full public URL of the uploaded image.
    """
    path, size = await save_upload(
        file,
        "media/images",
        ALLOWED_IMAGE_EXTENSIONS,
        ALLOWED_IMAGE_CONTENT_TYPES,
        MAX_IMAGE_SIZE,
    )
    base = get_base_url().rstrip("/")
    url = f"{base}/{path}"
    return {
        "url": url,
        "path": f"/{path}",
        "size": size,
        "message": "Image uploaded successfully",
    }
