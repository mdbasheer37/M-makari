from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_user, get_current_admin
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class NotifCreate(BaseModel):
    title: str
    body: Optional[str] = None
    notification_type: Optional[str] = None
    target_url: Optional[str] = None

@router.get("/")
def get_notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    notifs = db.query(models.UserNotification).filter(models.UserNotification.user_id == user.id).order_by(models.UserNotification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "is_read": n.is_read, "created_at": n.created_at.isoformat() if n.created_at else None, "notification": {"title": n.notification.title, "body": n.notification.body, "type": n.notification.notification_type} if n.notification else None} for n in notifs]

@router.post("/send")
def send_notification(data: NotifCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    notif = models.Notification(**data.dict())
    db.add(notif)
    db.flush()
    users = db.query(models.User).filter(models.User.is_active == True).all()
    for u in users:
        un = models.UserNotification(user_id=u.id, notification_id=notif.id)
        db.add(un)
    db.commit()
    return {"message": f"Sent to {len(users)} users"}

@router.patch("/{notif_id}/read")
def mark_read(notif_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    n = db.query(models.UserNotification).filter(models.UserNotification.id == notif_id, models.UserNotification.user_id == user.id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"message": "Marked as read"}
