from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_user
from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime, timezone

router = APIRouter()

VALID_CONTENT_TYPES = {t.value for t in models.ContentType}
VALID_STATUSES = {"pending", "downloading", "complete", "failed"}


class DownloadCreate(BaseModel):
    content_type: str
    content_id: int
    file_size: Optional[int] = None

    @model_validator(mode="after")
    def check_type(self):
        if self.content_type not in VALID_CONTENT_TYPES:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(VALID_CONTENT_TYPES))}")
        return self


class DownloadUpdate(BaseModel):
    progress: Optional[float] = None
    status: Optional[str] = None

    @model_validator(mode="after")
    def check_status(self):
        if self.status is not None and self.status not in VALID_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")
        if self.progress is not None and not (0 <= self.progress <= 100):
            raise ValueError("progress must be between 0 and 100")
        return self


def download_to_dict(d):
    return {
        "id": d.id, "content_type": d.content_type, "content_id": d.content_id,
        "file_size": d.file_size, "progress": d.progress, "status": d.status,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "completed_at": d.completed_at.isoformat() if d.completed_at else None,
    }


@router.get("/")
def get_downloads(db: Session = Depends(get_db), user=Depends(get_current_user)):
    dls = db.query(models.Download).filter(models.Download.user_id == user.id).order_by(models.Download.created_at.desc()).all()
    return [download_to_dict(d) for d in dls]


@router.post("/")
def start_download(data: DownloadCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Reuse an existing record for the same content instead of duplicating.
    existing = db.query(models.Download).filter(
        models.Download.user_id == user.id,
        models.Download.content_type == data.content_type,
        models.Download.content_id == data.content_id,
    ).first()
    if existing:
        existing.status = "pending"
        existing.progress = 0.0
        existing.completed_at = None
        db.commit()
        db.refresh(existing)
        return download_to_dict(existing)

    dl = models.Download(
        user_id=user.id, content_type=data.content_type, content_id=data.content_id,
        file_size=data.file_size, progress=0.0, status="pending",
    )
    db.add(dl)
    db.commit()
    db.refresh(dl)
    return download_to_dict(dl)


@router.patch("/{download_id}")
def update_download(download_id: int, data: DownloadUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dl = db.query(models.Download).filter(models.Download.id == download_id, models.Download.user_id == user.id).first()
    if not dl:
        raise HTTPException(status_code=404, detail="Not found")
    if data.progress is not None:
        dl.progress = data.progress
    if data.status is not None:
        dl.status = data.status
        if data.status == "complete":
            dl.progress = 100.0
            dl.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dl)
    return download_to_dict(dl)


@router.delete("/{download_id}")
def delete_download(download_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    dl = db.query(models.Download).filter(models.Download.id == download_id, models.Download.user_id == user.id).first()
    if not dl:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(dl)
    db.commit()
    return {"message": "Removed"}
