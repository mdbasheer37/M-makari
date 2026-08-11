from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
from auth_utils import get_current_admin

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
