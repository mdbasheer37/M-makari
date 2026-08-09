from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional, List
from database import get_db
import models
from auth_utils import get_current_user, get_current_admin, get_optional_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class LectureCreate(BaseModel):
    title_en: str
    title_ha: Optional[str] = None
    description_en: Optional[str] = None
    description_ha: Optional[str] = None
    category_id: Optional[int] = None
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    tags: Optional[str] = None
    is_featured: bool = False
    is_trending: bool = False
    date_recorded: Optional[datetime] = None

def lecture_to_dict(lec, db=None):
    return {
        "id": lec.id,
        "title_en": lec.title_en,
        "title_ha": lec.title_ha,
        "description_en": lec.description_en,
        "description_ha": lec.description_ha,
        "thumbnail": lec.thumbnail,
        "duration": lec.duration,
        "view_count": lec.view_count,
        "like_count": lec.like_count,
        "is_featured": lec.is_featured,
        "is_trending": lec.is_trending,
        "tags": lec.tags,
        "category": {"id": lec.category.id, "name_en": lec.category.name_en, "name_ha": lec.category.name_ha, "slug": lec.category.slug} if lec.category else None,
        "date_recorded": lec.date_recorded.isoformat() if lec.date_recorded else None,
        "created_at": lec.created_at.isoformat() if lec.created_at else None,
        "video_count": len(lec.videos) if lec.videos else 0,
        "audio_count": len(lec.audio_files) if lec.audio_files else 0,
    }

@router.get("/")
def get_lectures(
    skip: int = 0, limit: int = 20,
    category_id: Optional[int] = None,
    is_featured: Optional[bool] = None,
    is_trending: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Lecture).filter(models.Lecture.is_published == True)
    if category_id:
        q = q.filter(models.Lecture.category_id == category_id)
    if is_featured is not None:
        q = q.filter(models.Lecture.is_featured == is_featured)
    if is_trending is not None:
        q = q.filter(models.Lecture.is_trending == is_trending)
    total = q.count()
    lectures = q.order_by(desc(models.Lecture.created_at)).offset(skip).limit(limit).all()
    return {"total": total, "lectures": [lecture_to_dict(l) for l in lectures]}

@router.get("/featured")
def get_featured(db: Session = Depends(get_db)):
    lectures = db.query(models.Lecture).filter(
        models.Lecture.is_featured == True,
        models.Lecture.is_published == True
    ).order_by(desc(models.Lecture.created_at)).limit(10).all()
    return [lecture_to_dict(l) for l in lectures]

@router.get("/trending")
def get_trending(db: Session = Depends(get_db)):
    lectures = db.query(models.Lecture).filter(
        models.Lecture.is_trending == True,
        models.Lecture.is_published == True
    ).order_by(desc(models.Lecture.view_count)).limit(10).all()
    return [lecture_to_dict(l) for l in lectures]

@router.get("/latest")
def get_latest(db: Session = Depends(get_db)):
    lectures = db.query(models.Lecture).filter(
        models.Lecture.is_published == True
    ).order_by(desc(models.Lecture.created_at)).limit(20).all()
    return [lecture_to_dict(l) for l in lectures]

@router.get("/most-viewed")
def get_most_viewed(db: Session = Depends(get_db)):
    lectures = db.query(models.Lecture).filter(
        models.Lecture.is_published == True
    ).order_by(desc(models.Lecture.view_count)).limit(10).all()
    return [lecture_to_dict(l) for l in lectures]

@router.get("/{lecture_id}")
def get_lecture(lecture_id: int, db: Session = Depends(get_db)):
    lec = db.query(models.Lecture).filter(models.Lecture.id == lecture_id).first()
    if not lec:
        raise HTTPException(status_code=404, detail="Lecture not found")
    lec.view_count += 1
    db.commit()
    data = lecture_to_dict(lec)
    data["videos"] = [{"id": v.id, "title": v.title, "stream_url": v.stream_url, "youtube_url": v.youtube_url, "quality": v.quality, "duration": v.duration} for v in lec.videos]
    data["audio_files"] = [{"id": a.id, "title": a.title, "stream_url": a.stream_url, "duration": a.duration, "bitrate": a.bitrate} for a in lec.audio_files]
    return data

@router.post("/")
def create_lecture(data: LectureCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    lec = models.Lecture(**data.dict())
    db.add(lec)
    db.commit()
    db.refresh(lec)
    return lecture_to_dict(lec)

@router.put("/{lecture_id}")
def update_lecture(lecture_id: int, data: LectureCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    lec = db.query(models.Lecture).filter(models.Lecture.id == lecture_id).first()
    if not lec:
        raise HTTPException(status_code=404, detail="Not found")
    for key, val in data.dict(exclude_unset=True).items():
        setattr(lec, key, val)
    db.commit()
    return lecture_to_dict(lec)

@router.delete("/{lecture_id}")
def delete_lecture(lecture_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    lec = db.query(models.Lecture).filter(models.Lecture.id == lecture_id).first()
    if not lec:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(lec)
    db.commit()
    return {"message": "Deleted"}
