"""Shared helpers for YouTube URL handling and safe media uploads."""
import os
import re
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract an 11-character YouTube video ID from any common URL format:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
      - https://www.youtube.com/shorts/VIDEO_ID
      - https://music.youtube.com/watch?v=VIDEO_ID
    Returns None if no valid ID can be found — callers must handle that
    instead of blindly injecting the raw URL into an <iframe>.
    """
    if not url:
        return None
    url = url.strip()

    patterns = [
        r"(?:youtube\.com|music\.youtube\.com)/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            vid = m.group(1)
            if YOUTUBE_ID_RE.match(vid):
                return vid
    return None


def normalize_youtube_url(url: str) -> Optional[str]:
    """Return a canonical, safe embed URL for a YouTube link, or None if invalid."""
    vid = extract_youtube_id(url)
    if not vid:
        return None
    return f"https://www.youtube.com/embed/{vid}"


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
ALLOWED_VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-m4v", "application/octet-stream"}
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg"}
ALLOWED_AUDIO_CONTENT_TYPES = {"audio/mpeg", "audio/mp4", "audio/wav", "audio/x-wav", "audio/ogg", "application/octet-stream"}
MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100 MB


async def save_upload(
    file: UploadFile,
    directory: str,
    allowed_extensions: set,
    allowed_content_types: set,
    max_size: int,
) -> tuple[str, int]:
    """
    Stream an UploadFile to disk with a random UUID filename (never trusting
    the client-supplied filename), enforcing extension/content-type/size
    limits. Returns (relative_path, size_bytes). Raises HTTPException on
    any validation failure and cleans up any partial file.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed_extensions))}",
        )
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {file.content_type}")

    os.makedirs(directory, exist_ok=True)
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(directory, filename)

    size = 0
    try:
        with open(path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_size:
                    f.close()
                    os.remove(path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {max_size // (1024*1024)} MB upload limit",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    if size == 0:
        os.remove(path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    return path, size
