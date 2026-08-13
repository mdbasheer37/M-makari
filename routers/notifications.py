from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database import get_db
import models
from auth_utils import get_current_user, get_current_admin
from pydantic import BaseModel, field_validator
from typing import Optional

router = APIRouter()

class NotifCreate(BaseModel):
    title: str
    body: Optional[str] = None
    notification_type: Optional[str] = None
    target_url: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_required(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Title is required")
        return v

@router.get("/")
def get_notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    notifs = db.query(models.UserNotification).filter(models.UserNotification.user_id == user.id).order_by(models.UserNotification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "is_read": n.is_read, "created_at": n.created_at.isoformat() if n.created_at else None, "notification": {"title": n.notification.title, "body": n.notification.body, "type": n.notification.notification_type} if n.notification else None} for n in notifs]

@router.get("/unread-count")
def get_unread_count(db: Session = Depends(get_db), user=Depends(get_current_user)):
    count = db.query(models.UserNotification).filter(
        models.UserNotification.user_id == user.id,
        models.UserNotification.is_read == False,
    ).count()
    return {"count": count}

@router.post("/send")
def send_notification(data: NotifCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    notif = models.Notification(**data.dict())
    db.add(notif)
    db.flush()
    users = db.query(models.User).filter(models.User.is_active == True).all()
    for u in users:
        un = models.UserNotification(user_id=u.id, notification_id=notif.id)
        db.add(un)
    notif.is_sent = True
    notif.sent_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": f"Sent to {len(users)} users"}

@router.patch("/{notif_id}/read")
def mark_read(notif_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    n = db.query(models.UserNotification).filter(models.UserNotification.id == notif_id, models.UserNotification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    n.is_read = True
    n.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Marked as read"}

@router.patch("/read-all")
def mark_all_read(db: Session = Depends(get_db), user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    updated = db.query(models.UserNotification).filter(
        models.UserNotification.user_id == user.id,
        models.UserNotification.is_read == False,
    ).update({"is_read": True, "read_at": now}, synchronize_session=False)
    db.commit()
    return {"message": f"Marked {updated} notifications as read"}
