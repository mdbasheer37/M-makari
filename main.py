from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import os

from database import engine, Base
from routers import auth, lectures, videos, audio, categories, search, favorites, downloads, notifications, library, live, admin, users, prayer

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Makari Islamic TV API",
    description="Complete Islamic streaming platform for Malam Ibrahim Makari",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("media/videos", exist_ok=True)
os.makedirs("media/audio", exist_ok=True)
os.makedirs("media/images", exist_ok=True)
os.makedirs("media/pdfs", exist_ok=True)
os.makedirs("media/thumbnails", exist_ok=True)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(lectures.router, prefix="/api/lectures", tags=["Lectures"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(audio.router, prefix="/api/audio", tags=["Audio"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(favorites.router, prefix="/api/favorites", tags=["Favorites"])
app.include_router(downloads.router, prefix="/api/downloads", tags=["Downloads"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(library.router, prefix="/api/library", tags=["Library"])
app.include_router(live.router, prefix="/api/live", tags=["Live Streaming"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(prayer.router, prefix="/api/prayer", tags=["Prayer Times"])

@app.get("/")
async def root():
    return {"message": "Makari Islamic TV API", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
