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


@router.post("/wipe-demo")
def wipe_demo_data(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """
    Delete all seeded demo lectures, videos, audio and books.
    Keeps: users, categories, live streams, real uploaded content.
    Safe to call — only deletes records created by seed.py (first 20 lectures).
    """
    try:
        # Delete audio files linked to demo lectures (IDs 1-20)
        demo_ids = list(range(1, 21))

        audio_deleted = db.query(models.AudioFile).filter(
            models.AudioFile.lecture_id.in_(demo_ids)
        ).delete(synchronize_session=False)

        video_deleted = db.query(models.Video).filter(
            models.Video.lecture_id.in_(demo_ids)
        ).delete(synchronize_session=False)

        # Delete favorites linked to demo lectures
        db.query(models.Favorite).filter(
            models.Favorite.lecture_id.in_(demo_ids)
        ).delete(synchronize_session=False)

        # Delete watch history linked to demo lectures
        db.query(models.WatchHistory).filter(
            models.WatchHistory.lecture_id.in_(demo_ids)
        ).delete(synchronize_session=False)

        # Delete the demo lectures themselves
        lecture_deleted = db.query(models.Lecture).filter(
            models.Lecture.id.in_(demo_ids)
        ).delete(synchronize_session=False)

        # Delete demo books (first 5)
        book_deleted = db.query(models.Book).filter(
            models.Book.id.in_(list(range(1, 6)))
        ).delete(synchronize_session=False)

        # Delete demo live streams
        db.query(models.LiveStream).filter(
            models.LiveStream.id.in_([1, 2, 3])
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
