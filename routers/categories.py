from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
from auth_utils import get_current_admin

router = APIRouter()

class CategoryCreate(BaseModel):
    name_en: str
    name_ha: Optional[str] = None
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0

@router.get("/")
def get_categories(db: Session = Depends(get_db)):
    cats = db.query(models.Category).filter(models.Category.is_active == True).order_by(models.Category.sort_order).all()
    return [{"id": c.id, "name_en": c.name_en, "name_ha": c.name_ha, "slug": c.slug, "icon": c.icon, "color": c.color, "thumbnail": c.thumbnail, "lecture_count": len(c.lectures)} for c in cats]

@router.post("/")
def create_category(data: CategoryCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    cat = models.Category(**data.dict())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.get("/{slug}/lectures")
def get_category_lectures(slug: str, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    cat = db.query(models.Category).filter(models.Category.slug == slug).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    from sqlalchemy import desc
    lectures = db.query(models.Lecture).filter(
        models.Lecture.category_id == cat.id,
        models.Lecture.is_published == True
    ).order_by(desc(models.Lecture.created_at)).offset(skip).limit(limit).all()
    return {"category": {"id": cat.id, "name_en": cat.name_en, "name_ha": cat.name_ha}, "lectures": [{"id": l.id, "title_en": l.title_en, "title_ha": l.title_ha, "thumbnail": l.thumbnail, "duration": l.duration, "view_count": l.view_count} for l in lectures]}
