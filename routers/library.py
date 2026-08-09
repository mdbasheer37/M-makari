from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_admin
from pydantic import BaseModel
from typing import Optional
import shutil, os, uuid

router = APIRouter()

class BookCreate(BaseModel):
    title_en: str
    title_ha: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    file_path: Optional[str] = None
    category: Optional[str] = None
    language: str = "en"
    is_downloadable: bool = True

@router.get("/books")
def get_books(category: str = None, db: Session = Depends(get_db)):
    q = db.query(models.Book)
    if category:
        q = q.filter(models.Book.category == category)
    books = q.all()
    return [{"id": b.id, "title_en": b.title_en, "title_ha": b.title_ha, "author": b.author, "cover_image": b.cover_image, "category": b.category, "language": b.language, "page_count": b.page_count, "download_count": b.download_count, "is_downloadable": b.is_downloadable} for b in books]

@router.get("/books/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Not found")
    return book

@router.post("/books")
def create_book(data: BookCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    book = models.Book(**data.dict())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book

@router.post("/books/upload")
async def upload_book(
    title_en: str = Form(...),
    author: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    filename = f"{uuid.uuid4()}.pdf"
    path = f"media/pdfs/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    size = os.path.getsize(path)
    book = models.Book(title_en=title_en, author=author, file_path=f"/{path}", file_size=size)
    db.add(book)
    db.commit()
    return {"id": book.id, "file_path": book.file_path}
