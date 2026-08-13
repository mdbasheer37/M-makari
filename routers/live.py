from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_admin
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from fastapi import HTTPException
from datetime import timezone

router = APIRouter()

class LiveCreate(BaseModel):
    title: str
    description: Optional[str] = None
    stream_url: str
    thumbnail: Optional[str] = None
    stream_type: Optional[str] = None
    scheduled_at: Optional[datetime] = None


def stream_to_dict(s):
    now = datetime.now(timezone.utc)
    if s.is_live:
        status = "live"
    elif s.scheduled_at and s.scheduled_at > now:
        status = "scheduled"
    else:
        status = "offline"
    return {
        "id": s.id, "title": s.title, "description": s.description, "stream_url": s.stream_url,
        "thumbnail": s.thumbnail, "stream_type": s.stream_type, "is_live": s.is_live,
        "viewer_count": s.viewer_count, "status": status,
        "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
    }


@router.get("/")
def get_live_streams(db: Session = Depends(get_db)):
    streams = db.query(models.LiveStream).order_by(models.LiveStream.created_at.desc()).all()
    return [stream_to_dict(s) for s in streams]

@router.get("/active")
def get_active_streams(db: Session = Depends(get_db)):
    streams = db.query(models.LiveStream).filter(models.LiveStream.is_live == True).all()
    return [stream_to_dict(s) for s in streams]

@router.post("/")
def create_stream(data: LiveCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    if not data.stream_url.strip():
        raise HTTPException(status_code=400, detail="Stream URL is required")
    stream = models.LiveStream(**data.dict())
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return stream_to_dict(stream)

@router.patch("/{stream_id}/toggle")
def toggle_live(stream_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    stream = db.query(models.LiveStream).filter(models.LiveStream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Not found")
    stream.is_live = not stream.is_live
    if stream.is_live:
        stream.started_at = datetime.now(timezone.utc)
    else:
        stream.ended_at = datetime.now(timezone.utc)
    db.commit()
    return stream_to_dict(stream)

@router.delete("/{stream_id}")
def delete_stream(stream_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    stream = db.query(models.LiveStream).filter(models.LiveStream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(stream)
    db.commit()
    return {"message": "Deleted"}
