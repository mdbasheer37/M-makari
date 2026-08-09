from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_user, get_password_hash
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    language: Optional[str] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

@router.get("/profile")
def get_profile(user=Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "avatar": user.avatar, "language": user.language, "role": user.role, "created_at": user.created_at.isoformat() if user.created_at else None}

@router.put("/profile")
def update_profile(data: ProfileUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    for key, val in data.dict(exclude_none=True).items():
        setattr(user, key, val)
    db.commit()
    return {"message": "Profile updated"}

@router.post("/change-password")
def change_password(data: PasswordChange, db: Session = Depends(get_db), user=Depends(get_current_user)):
    from auth_utils import verify_password
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

@router.get("/history")
def get_watch_history(db: Session = Depends(get_db), user=Depends(get_current_user)):
    history = db.query(models.WatchHistory).filter(
        models.WatchHistory.user_id == user.id
    ).order_by(models.WatchHistory.last_watched.desc()).limit(30).all()
    return [{"id": h.id, "lecture_id": h.lecture_id, "progress": h.progress, "last_watched": h.last_watched.isoformat() if h.last_watched else None, "lecture": {"title_en": h.lecture.title_en, "thumbnail": h.lecture.thumbnail} if h.lecture else None} for h in history]
