from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from auth_utils import get_current_admin
from pydantic import BaseModel
from typing import Optional
import shutil, os, uuid

router = APIRouter()

MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB


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


def book_to_dict(b):
    return {
        "id": b.id, "title_en": b.title_en, "title_ha": b.title_ha, "author": b.author,
        "description": b.description, "cover_image": b.cover_image, "file_path": b.file_path,
        "file_size": b.file_size, "page_count": b.page_count, "category": b.category,
        "language": b.language, "download_count": b.download_count,
        "is_downloadable": b.is_downloadable,
    }


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
    return book_to_dict(book)

@router.post("/books")
def create_book(data: BookCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    book = models.Book(**data.dict())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book_to_dict(book)

@router.post("/books/{book_id}/download")
def register_download(book_id: int, db: Session = Depends(get_db)):
    """Bump the download counter for a book (called by the frontend when a download starts)."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Not found")
    if not book.is_downloadable:
        raise HTTPException(status_code=403, detail="This book is not downloadable")
    if not book.file_path:
        raise HTTPException(status_code=404, detail="No file available for this book")
    book.download_count = (book.download_count or 0) + 1
    db.commit()
    return {"file_path": book.file_path, "download_count": book.download_count}

@router.post("/books/upload")
async def upload_book(
    title_en: str = Form(...),
    author: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    if not title_en.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    # Validate extension and content type — never trust the client filename.
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".pdf" or file.content_type not in ("application/pdf", "application/x-pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    os.makedirs("media/pdfs", exist_ok=True)
    filename = f"{uuid.uuid4()}.pdf"
    path = f"media/pdfs/{filename}"

    size = 0
    try:
        with open(path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_PDF_SIZE:
                    f.close()
                    os.remove(path)
                    raise HTTPException(status_code=413, detail="PDF exceeds the 50 MB upload limit")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Basic magic-byte check so a renamed non-PDF file isn't stored as one.
    with open(path, "rb") as f:
        header = f.read(5)
    if header != b"%PDF-":
        os.remove(path)
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF")

    book = models.Book(title_en=title_en, author=author, file_path=f"/{path}", file_size=size, is_downloadable=True)
    db.add(book)
    db.commit()
    db.refresh(book)
    return {"id": book.id, "file_path": book.file_path, "file_size": size}
