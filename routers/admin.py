from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db
import models
from auth_utils import get_current_admin

router = APIRouter()

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    total_users = db.query(models.User).count()
    total_lectures = db.query(models.Lecture).count()
    total_videos = db.query(models.Video).count()
    total_audio = db.query(models.AudioFile).count()
    total_books = db.query(models.Book).count()
    total_views = db.query(func.sum(models.Lecture.view_count)).scalar() or 0
    live_streams = db.query(models.LiveStream).filter(models.LiveStream.is_live == True).count()
    return {
        "total_users": total_users,
        "total_lectures": total_lectures,
        "total_videos": total_videos,
        "total_audio": total_audio,
        "total_books": total_books,
        "total_views": total_views,
        "live_streams": live_streams,
    }

@router.get("/users")
def get_all_users(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    total = db.query(models.User).count()
    return {"total": total, "users": [{"id": u.id, "username": u.username, "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat() if u.created_at else None} for u in users]}

@router.patch("/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    user.is_active = not user.is_active
    db.commit()
    return {"is_active": user.is_active}

@router.patch("/users/{user_id}/role")
def set_role(user_id: int, role: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    user.role = role
    db.commit()
    return {"role": user.role}

@router.get("/recent-lectures")
def recent_lectures(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    lectures = db.query(models.Lecture).order_by(desc(models.Lecture.created_at)).limit(10).all()
    return [{"id": l.id, "title_en": l.title_en, "view_count": l.view_count, "is_published": l.is_published, "created_at": l.created_at.isoformat() if l.created_at else None} for l in lectures]
