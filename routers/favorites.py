from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_user
from pydantic import BaseModel, model_validator
from typing import Optional

router = APIRouter()

VALID_CONTENT_TYPES = {t.value for t in models.ContentType}


class FavoriteCreate(BaseModel):
    lecture_id: Optional[int] = None
    book_id: Optional[int] = None
    content_type: str

    @model_validator(mode="after")
    def check_target(self):
        if not self.lecture_id and not self.book_id:
            raise ValueError("Either lecture_id or book_id is required")
        if self.lecture_id and self.book_id:
            raise ValueError("Provide only one of lecture_id or book_id")
        if self.content_type not in VALID_CONTENT_TYPES:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(VALID_CONTENT_TYPES))}")
        return self


@router.get("/")
def get_favorites(db: Session = Depends(get_db), user=Depends(get_current_user)):
    favs = db.query(models.Favorite).filter(models.Favorite.user_id == user.id).all()
    result = []
    for f in favs:
        item = {
            "id": f.id, "lecture_id": f.lecture_id, "book_id": f.book_id,
            "content_type": f.content_type, "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        if f.lecture:
            item["lecture"] = {"id": f.lecture.id, "title_en": f.lecture.title_en, "thumbnail": f.lecture.thumbnail, "duration": f.lecture.duration}
        result.append(item)
    return result

@router.post("/")
def add_favorite(data: FavoriteCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(models.Favorite).filter(models.Favorite.user_id == user.id)
    if data.lecture_id:
        q = q.filter(models.Favorite.lecture_id == data.lecture_id)
    else:
        q = q.filter(models.Favorite.book_id == data.book_id)
    existing = q.first()
    if existing:
        return {"id": existing.id, "message": "Already favorited"}
    fav = models.Favorite(user_id=user.id, **data.dict())
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return {"id": fav.id, "message": "Added to favorites"}

@router.delete("/{favorite_id}")
def remove_favorite(favorite_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    fav = db.query(models.Favorite).filter(models.Favorite.id == favorite_id, models.Favorite.user_id == user.id).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(fav)
    db.commit()
    return {"message": "Removed from favorites"}

@router.delete("/lecture/{lecture_id}")
def remove_favorite_by_lecture(lecture_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Convenience endpoint so the frontend can un-favorite without tracking the favorite row id."""
    fav = db.query(models.Favorite).filter(
        models.Favorite.lecture_id == lecture_id, models.Favorite.user_id == user.id
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(fav)
    db.commit()
    return {"message": "Removed from favorites"}
