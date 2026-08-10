from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db
import models
from auth_utils import get_current_admin

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
def get_all_users(skip: int = 0, limit: int = 50,
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


# ── EMERGENCY: No auth required — only works if zero users exist ──
@router.post("/setup")
def first_time_setup(db: Session = Depends(get_db)):
    """
    First-time setup endpoint. Creates admin account.
    Safe: only works when the users table is completely empty.
    After first use, this endpoint becomes harmless (returns 'already set up').
    """
    from auth_utils import get_password_hash

    user_count = db.query(models.User).count()
    if user_count > 0:
        return {
            "message": "Already set up — admin exists",
            "login_email": "admin@makariilamictv.com",
            "hint": "Use /api/auth/login to get your token",
        }

    # Create admin
    admin = models.User(
        username="admin",
        email="admin@makariilamictv.com",
        full_name="Makari TV Admin",
        hashed_password=get_password_hash("admin123"),
        role=models.UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    # Seed categories and demo content
    try:
        from seed import seed
        seed()
    except Exception as e:
        pass

    return {
        "message": "✅ Setup complete!",
        "email": "admin@makariilamictv.com",
        "password": "admin123",
        "next_step": "Login at /api/auth/login",
    }
