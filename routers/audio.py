from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
from auth_utils import get_current_admin

router = APIRouter()


class AudioCreate(BaseModel):
    lecture_id: int
    title: str
    stream_url: Optional[str] = None
    file_path: Optional[str] = None
    duration: Optional[int] = None
    bitrate: Optional[int] = None
    is_downloadable: bool = True


@router.get("/")
def get_audio_files(lecture_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.AudioFile)
    if lecture_id:
        q = q.filter(models.AudioFile.lecture_id == lecture_id)
    files = q.all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "stream_url": a.stream_url,
            "file_path": a.file_path,
            "duration": a.duration,
            "bitrate": a.bitrate,
            "play_count": a.play_count,
            "lecture_id": a.lecture_id,
            "is_downloadable": a.is_downloadable,
        }
        for a in files
    ]


@router.post("/")
def create_audio(
    data: AudioCreate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    # Verify lecture exists
    lec = db.query(models.Lecture).filter(models.Lecture.id == data.lecture_id).first()
    if not lec:
        raise HTTPException(status_code=404, detail=f"Lecture {data.lecture_id} not found")
    audio = models.AudioFile(
        lecture_id=data.lecture_id,
        title=data.title,
        stream_url=data.stream_url,
        file_path=data.file_path,
        duration=data.duration,
        bitrate=data.bitrate,
        is_downloadable=data.is_downloadable,
        play_count=0,
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return {
        "id": audio.id,
        "title": audio.title,
        "stream_url": audio.stream_url,
        "lecture_id": audio.lecture_id,
        "message": "Audio added successfully",
    }


@router.get("/{audio_id}")
def get_audio(audio_id: int, db: Session = Depends(get_db)):
    audio = db.query(models.AudioFile).filter(models.AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Not found")
    audio.play_count = (audio.play_count or 0) + 1
    db.commit()
    return {
        "id": audio.id,
        "title": audio.title,
        "stream_url": audio.stream_url,
        "file_path": audio.file_path,
        "duration": audio.duration,
        "bitrate": audio.bitrate,
    }


@router.delete("/{audio_id}")
def delete_audio(audio_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    audio = db.query(models.AudioFile).filter(models.AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(audio)
    db.commit()
    return {"message": "Deleted"}
