from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_admin, get_current_user
from pydantic import BaseModel
from typing import Optional
import shutil, os, uuid

router = APIRouter()

class VideoCreate(BaseModel):
    lecture_id: int
    title: str
    stream_url: Optional[str] = None
    youtube_url: Optional[str] = None
    quality: str = "720p"
    duration: Optional[int] = None
    is_downloadable: bool = True

@router.get("/")
def get_videos(lecture_id: int = None, db: Session = Depends(get_db)):
    q = db.query(models.Video)
    if lecture_id:
        q = q.filter(models.Video.lecture_id == lecture_id)
    videos = q.all()
    return [{"id": v.id, "title": v.title, "stream_url": v.stream_url, "youtube_url": v.youtube_url, "file_path": v.file_path, "quality": v.quality, "duration": v.duration, "view_count": v.view_count, "lecture_id": v.lecture_id} for v in videos]

@router.post("/")
def create_video(data: VideoCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    video = models.Video(**data.dict())
    db.add(video)
    db.commit()
    db.refresh(video)
    return video

@router.get("/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Not found")
    video.view_count += 1
    db.commit()
    return {"id": video.id, "title": video.title, "stream_url": video.stream_url, "youtube_url": video.youtube_url, "quality": video.quality, "duration": video.duration}

@router.post("/upload")
async def upload_video(
    lecture_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = f"media/videos/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    size = os.path.getsize(path)
    video = models.Video(lecture_id=lecture_id, title=title, file_path=f"/{path}", file_size=size)
    db.add(video)
    db.commit()
    return {"id": video.id, "file_path": video.file_path}
