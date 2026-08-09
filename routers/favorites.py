from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_user
from pydantic import BaseModel

router = APIRouter()

class FavoriteCreate(BaseModel):
    lecture_id: int = None
    book_id: int = None
    content_type: str

@router.get("/")
def get_favorites(db: Session = Depends(get_db), user=Depends(get_current_user)):
    favs = db.query(models.Favorite).filter(models.Favorite.user_id == user.id).all()
    result = []
    for f in favs:
        item = {"id": f.id, "content_type": f.content_type, "created_at": f.created_at.isoformat() if f.created_at else None}
        if f.lecture:
            item["lecture"] = {"id": f.lecture.id, "title_en": f.lecture.title_en, "thumbnail": f.lecture.thumbnail, "duration": f.lecture.duration}
        result.append(item)
    return result

@router.post("/")
def add_favorite(data: FavoriteCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    existing = db.query(models.Favorite).filter(
        models.Favorite.user_id == user.id,
        models.Favorite.lecture_id == data.lecture_id
    ).first()
    if existing:
        return {"message": "Already favorited", "id": existing.id}
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
