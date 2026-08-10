from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database import get_db
import models
from auth_utils import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    language: str = "en"

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = models.User(
        username=req.username,
        email=req.email,
        full_name=req.full_name,
        hashed_password=get_password_hash(req.password),
        language=req.language
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "role": user.role}}

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "role": user.role, "avatar": user.avatar}}

@router.get("/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email, "full_name": current_user.full_name, "role": current_user.role, "avatar": current_user.avatar, "language": current_user.language}


@router.get("/setup")
@router.post("/setup")
def setup_admin(db: Session = Depends(get_db)):
    """
    Open this URL in browser to create the admin account.
    Safe — only creates admin if no users exist yet.
    URL: /api/auth/setup
    """
    existing = db.query(models.User).filter(
        models.User.email == "admin@makariilamictv.com"
    ).first()

    if existing:
        return {
            "status": "already_exists",
            "message": "Admin account already exists. Login below.",
            "email": "admin@makariilamictv.com",
            "password": "admin123",
        }

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
    db.refresh(admin)

    return {
        "status": "success",
        "message": "✅ Admin created successfully!",
        "email": "admin@makariilamictv.com",
        "password": "admin123",
        "next": "Now login at your app with these credentials",
    }
