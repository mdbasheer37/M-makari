from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_admin
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

class LiveCreate(BaseModel):
    title: str
    description: Optional[str] = None
    stream_url: str
    thumbnail: Optional[str] = None
    stream_type: Optional[str] = None
    scheduled_at: Optional[datetime] = None

@router.get("/")
def get_live_streams(db: Session = Depends(get_db)):
    streams = db.query(models.LiveStream).order_by(models.LiveStream.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "description": s.description, "stream_url": s.stream_url, "thumbnail": s.thumbnail, "stream_type": s.stream_type, "is_live": s.is_live, "viewer_count": s.viewer_count, "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None} for s in streams]

@router.get("/active")
def get_active_streams(db: Session = Depends(get_db)):
    streams = db.query(models.LiveStream).filter(models.LiveStream.is_live == True).all()
    return [{"id": s.id, "title": s.title, "stream_url": s.stream_url, "thumbnail": s.thumbnail, "viewer_count": s.viewer_count, "is_live": True} for s in streams]

@router.post("/")
def create_stream(data: LiveCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    stream = models.LiveStream(**data.dict())
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return stream

@router.patch("/{stream_id}/toggle")
def toggle_live(stream_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    stream = db.query(models.LiveStream).filter(models.LiveStream.id == stream_id).first()
    if not stream:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    stream.is_live = not stream.is_live
    db.commit()
    return {"is_live": stream.is_live}
