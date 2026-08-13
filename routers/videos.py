from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, model_validator
from typing import Optional
from database import get_db
import models
from auth_utils import get_current_admin
from media_utils import normalize_youtube_url, save_upload, ALLOWED_VIDEO_EXTENSIONS, ALLOWED_VIDEO_CONTENT_TYPES, MAX_VIDEO_SIZE

router = APIRouter()


class VideoCreate(BaseModel):
    lecture_id: int
    title: str
    stream_url: Optional[str] = None
    youtube_url: Optional[str] = None
    file_path: Optional[str] = None
    quality: str = "720p"
    duration: Optional[int] = None
    is_downloadable: bool = True

    @model_validator(mode="after")
    def check_source(self):
        if not self.stream_url and not self.youtube_url and not self.file_path:
            raise ValueError("Provide at least one of stream_url, youtube_url, or file_path")
        if self.youtube_url:
            normalized = normalize_youtube_url(self.youtube_url)
            if normalized:
                # Genuinely a YouTube link — canonicalize it.
                self.youtube_url = normalized
                if not self.stream_url:
                    self.stream_url = normalized
            else:
                # The admin form has a single "YouTube / Video URL" field that
                # accepts either a YouTube link or a direct MP4/stream URL, and
                # sends whatever was typed as both youtube_url and stream_url.
                # Rather than reject a valid direct video link because it
                # isn't YouTube, just treat it as a direct stream instead.
                if not self.stream_url:
                    self.stream_url = self.youtube_url
                self.youtube_url = None
        return self


@router.get("/")
def get_videos(lecture_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Video)
    if lecture_id:
        q = q.filter(models.Video.lecture_id == lecture_id)
    videos = q.all()
    return [
        {
            "id": v.id,
            "title": v.title,
            "stream_url": v.stream_url,
            "youtube_url": v.youtube_url,
            "file_path": v.file_path,
            "quality": v.quality,
            "duration": v.duration,
            "view_count": v.view_count,
            "lecture_id": v.lecture_id,
            "is_downloadable": v.is_downloadable,
        }
        for v in videos
    ]


@router.post("/")
def create_video(
    data: VideoCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    # Verify lecture exists
    lec = db.query(models.Lecture).filter(models.Lecture.id == data.lecture_id).first()
    if not lec:
        raise HTTPException(status_code=404, detail=f"Lecture {data.lecture_id} not found")

    video = models.Video(
        lecture_id=data.lecture_id,
        title=data.title,
        stream_url=data.stream_url,
        youtube_url=data.youtube_url,
        file_path=data.file_path,
        quality=data.quality,
        duration=data.duration,
        is_downloadable=data.is_downloadable,
        view_count=0,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return {
        "id": video.id,
        "title": video.title,
        "youtube_url": video.youtube_url,
        "stream_url": video.stream_url,
        "lecture_id": video.lecture_id,
        "message": "Video added successfully",
    }


@router.post("/upload")
async def upload_video(
    lecture_id: int = Form(...),
    title: str = Form(...),
    quality: str = Form("720p"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    lec = db.query(models.Lecture).filter(models.Lecture.id == lecture_id).first()
    if not lec:
        raise HTTPException(status_code=404, detail=f"Lecture {lecture_id} not found")

    path, size = await save_upload(file, "media/videos", ALLOWED_VIDEO_EXTENSIONS, ALLOWED_VIDEO_CONTENT_TYPES, MAX_VIDEO_SIZE)

    video = models.Video(
        lecture_id=lecture_id, title=title, file_path=f"/{path}", stream_url=f"/{path}",
        quality=quality, file_size=size, is_downloadable=True, view_count=0,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return {"id": video.id, "title": video.title, "stream_url": video.stream_url, "file_size": size, "message": "Video uploaded successfully"}


@router.get("/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Not found")
    video.view_count = (video.view_count or 0) + 1
    db.commit()
    return {
        "id": video.id,
        "title": video.title,
        "stream_url": video.stream_url,
        "youtube_url": video.youtube_url,
        "quality": video.quality,
        "duration": video.duration,
    }


@router.delete("/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(video)
    db.commit()
    return {"message": "Deleted"}
