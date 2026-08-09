from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_user

router = APIRouter()

@router.get("/")
def get_downloads(db: Session = Depends(get_db), user=Depends(get_current_user)):
    dls = db.query(models.Download).filter(models.Download.user_id == user.id).all()
    return [{"id": d.id, "content_type": d.content_type, "content_id": d.content_id, "file_size": d.file_size, "progress": d.progress, "status": d.status, "created_at": d.created_at.isoformat() if d.created_at else None} for d in dls]
