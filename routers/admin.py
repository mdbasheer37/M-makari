from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db
import models
from auth_utils import get_current_admin, ensure_admin_from_env, VALID_ROLES

router = APIRouter()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    return {
        "total_users":    db.query(models.User).count(),
        "total_lectures": db.query(models.Lecture).count(),
        "total_videos":   db.query(models.Video).count(),
        "total_audio":    db.query(models.AudioFile).count(),
        "total_books":    db.query(models.Book).count(),
        "total_views":    db.query(func.sum(models.Lecture.view_count)).scalar() or 0,
        "live_streams":   db.query(models.LiveStream).filter(models.LiveStream.is_live == True).count(),
    }


@router.get("/users")
def get_all_users(skip: int = 0, limit: int = Query(50, le=200),
                  db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    total = db.query(models.User).count()
    return {
        "total": total,
        "users": [
            {"id": u.id, "username": u.username, "email": u.email,
             "full_name": u.full_name, "role": u.role,
             "is_active": u.is_active,
             "created_at": u.created_at.isoformat() if u.created_at else None}
            for u in users
        ],
    }


@router.patch("/users/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    user.is_active = not user.is_active
    db.commit()
    return {"is_active": user.is_active}


@router.patch("/users/{user_id}/role")
def set_role(user_id: int, role: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    user.role = role
    db.commit()
    return {"role": user.role}


@router.get("/recent-lectures")
def recent_lectures(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    lectures = db.query(models.Lecture).order_by(desc(models.Lecture.created_at)).limit(10).all()
    return [
        {"id": l.id, "title_en": l.title_en, "view_count": l.view_count,
         "is_published": l.is_published,
         "created_at": l.created_at.isoformat() if l.created_at else None}
        for l in lectures
    ]


@router.post("/reseed")
def reseed_database(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """Force re-run the seeder — safe, skips existing records."""
    try:
        from seed import seed
        seed()
        return {"message": "✅ Database re-seeded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── First-time setup: no auth required, but creates nothing on its own ──
@router.get("/setup")
@router.post("/setup")
def first_time_setup(db: Session = Depends(get_db)):
    """
    First-time setup endpoint.

    Does NOT create any predictable/default admin account. It only creates
    an admin if ADMIN_EMAIL and ADMIN_PASSWORD are configured as environment
    variables on the server — the same check that already runs automatically
    at startup (see main.py lifespan / auth_utils.ensure_admin_from_env).
    """
    admin = ensure_admin_from_env(db)
    if admin:
        # Seed categories and demo content alongside the admin account
        try:
            from seed import seed
            seed()
        except Exception:
            pass
        return {
            "message": f"✅ Setup complete! Admin: {admin.email}",
            "next_step": "Login at /api/auth/login with the credentials you configured",
        }

    if db.query(models.User).filter(models.User.role == models.UserRole.admin).first():
        return {
            "message": "Already set up — an admin account exists",
            "hint": "Use /api/auth/login to get your token",
        }

    raise HTTPException(
        status_code=400,
        detail=(
            "No admin account exists yet. Set ADMIN_EMAIL and ADMIN_PASSWORD "
            "(min 8 characters) as environment variables on the server, "
            "then call this endpoint again."
        ),
    )


DEMO_LECTURE_TITLES = [
    "Tafsir of Surah Al-Baqarah - Lesson 1", "Tafsir of Surah Al-Imran",
    "The Importance of Prayer in Islam", "How to Perform Prayer Correctly",
    "Ramadan: The Month of Blessings", "Marriage in Islam - Part 1",
    "Upbringing: How to Raise Children", "Islamic Creed - Pillars of Faith",
    "40 Hadiths of Imam Nawawi - Lesson 1", "Women in Islam: Their Status",
    "Youth and Modern Challenges", "Questions and Answers - Part 1",
    "Remembrance and Supplication", "Tafsir of Surah Yasin",
    "Character of Prophet Muhammad SAW", "Zakat: Its Rulings",
    "Fasting: Conditions and Rulings", "Hajj and Umrah",
    "Repentance and Seeking Forgiveness", "Afterlife: The World to Come",
]
DEMO_BOOK_TITLES = [
    "Fiqhus Sunnah", "Riyadus Salihin", "Fortress of the Muslim",
    "Islamic Creed", "The Sealed Nectar",
]
DEMO_LIVESTREAM_TITLES = ["Makari Live TV", "Friday Tafsir Live", "Ramadan Special Broadcast"]


@router.post("/wipe-demo")
def wipe_demo_data(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """
    Delete all seeded demo lectures, videos, audio, books and live streams.
    Keeps: users, categories, real content added via the admin dashboard.
    Matches by the exact known demo titles (defined in seed.py) rather than
    assumed ID ranges, so this is safe to call regardless of what order
    content was created in, and never touches real content that happens to
    share an ID with old demo rows.
    """
    try:
        demo_lecture_ids = [
            row.id for row in db.query(models.Lecture.id).filter(
                models.Lecture.title_en.in_(DEMO_LECTURE_TITLES)
            ).all()
        ]

        audio_deleted = 0
        video_deleted = 0
        lecture_deleted = 0
        if demo_lecture_ids:
            audio_deleted = db.query(models.AudioFile).filter(
                models.AudioFile.lecture_id.in_(demo_lecture_ids)
            ).delete(synchronize_session=False)

            video_deleted = db.query(models.Video).filter(
                models.Video.lecture_id.in_(demo_lecture_ids)
            ).delete(synchronize_session=False)

            db.query(models.Favorite).filter(
                models.Favorite.lecture_id.in_(demo_lecture_ids)
            ).delete(synchronize_session=False)

            db.query(models.WatchHistory).filter(
                models.WatchHistory.lecture_id.in_(demo_lecture_ids)
            ).delete(synchronize_session=False)

            lecture_deleted = db.query(models.Lecture).filter(
                models.Lecture.id.in_(demo_lecture_ids)
            ).delete(synchronize_session=False)

        book_deleted = db.query(models.Book).filter(
            models.Book.title_en.in_(DEMO_BOOK_TITLES)
        ).delete(synchronize_session=False)

        db.query(models.LiveStream).filter(
            models.LiveStream.title.in_(DEMO_LIVESTREAM_TITLES)
        ).delete(synchronize_session=False)

        db.commit()

        return {
            "message": f"✅ Demo data deleted successfully",
            "deleted": {
                "lectures": lecture_deleted,
                "videos": video_deleted,
                "audio": audio_deleted,
                "books": book_deleted,
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
