from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from database import get_db
import models

router = APIRouter()

@router.get("/")
def search(
    q: str = Query(..., min_length=2),
    content_type: str = None,
    category_id: int = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    results = {"lectures": [], "books": [], "total": 0}
    if not content_type or content_type == "lecture":
        query = db.query(models.Lecture).filter(
            models.Lecture.is_published == True,
            or_(
                models.Lecture.title_en.ilike(f"%{q}%"),
                models.Lecture.title_ha.ilike(f"%{q}%"),
                models.Lecture.description_en.ilike(f"%{q}%"),
                models.Lecture.tags.ilike(f"%{q}%")
            )
        )
        if category_id:
            query = query.filter(models.Lecture.category_id == category_id)
        lectures = query.order_by(desc(models.Lecture.view_count)).offset(skip).limit(limit).all()
        results["lectures"] = [{"id": l.id, "title_en": l.title_en, "title_ha": l.title_ha, "thumbnail": l.thumbnail, "duration": l.duration, "view_count": l.view_count, "type": "lecture"} for l in lectures]
    if not content_type or content_type == "book":
        books = db.query(models.Book).filter(
            or_(
                models.Book.title_en.ilike(f"%{q}%"),
                models.Book.title_ha.ilike(f"%{q}%"),
                models.Book.description.ilike(f"%{q}%")
            )
        ).limit(10).all()
        results["books"] = [{"id": b.id, "title_en": b.title_en, "cover_image": b.cover_image, "type": "book"} for b in books]
    results["total"] = len(results["lectures"]) + len(results["books"])
    return results
