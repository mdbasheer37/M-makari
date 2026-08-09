from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_admin
from pydantic import BaseModel
from typing import Optional
import shutil, os, uuid

router = APIRouter()

class AudioCreate(BaseModel):
    lecture_id: int
    title: str
    stream_url: Optional[str] = None
    duration: Optional[int] = None
    bitrate: Optional[int] = None
    is_downloadable: bool = True

@router.get("/")
def get_audio_files(lecture_id: int = None, db: Session = Depends(get_db)):
    q = db.query(models.AudioFile)
    if lecture_id:
        q = q.filter(models.AudioFile.lecture_id == lecture_id)
    files = q.all()
    return [{"id": a.id, "title": a.title, "stream_url": a.stream_url, "file_path": a.file_path, "duration": a.duration, "bitrate": a.bitrate, "play_count": a.play_count, "lecture_id": a.lecture_id, "is_downloadable": a.is_downloadable} for a in files]

@router.post("/")
def create_audio(data: AudioCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    audio = models.AudioFile(**data.dict())
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio

@router.post("/upload")
async def upload_audio(
    lecture_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = f"media/audio/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    size = os.path.getsize(path)
    audio = models.AudioFile(lecture_id=lecture_id, title=title, file_path=f"/{path}", file_size=size)
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return {"id": audio.id, "file_path": audio.file_path}

@router.get("/{audio_id}")
def get_audio(audio_id: int, db: Session = Depends(get_db)):
    audio = db.query(models.AudioFile).filter(models.AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Not found")
    audio.play_count += 1
    db.commit()
    return {"id": audio.id, "title": audio.title, "stream_url": audio.stream_url, "file_path": audio.file_path, "duration": audio.duration}
