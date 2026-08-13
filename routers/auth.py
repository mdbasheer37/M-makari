from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, field_validator
from database import get_db
import models
from auth_utils import get_password_hash, verify_password, create_access_token, get_current_user, ensure_admin_from_env

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str
    language: str = "en"

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        v = v.strip()
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters")
        return v

    @field_validator("full_name")
    @classmethod
    def full_name_valid(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Full name is required")
        return v[:100]

    @field_validator("password")
    @classmethod
    def password_valid(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = req.email.lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = models.User(
        username=req.username,
        email=email,
        full_name=req.full_name,
        hashed_password=get_password_hash(req.password),
        language=req.language
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email or username already registered")
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "role": user.role}}

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
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
    First-admin bootstrap endpoint.

    This does NOT create any credentials itself. It only creates an admin
    account if the operator has set ADMIN_EMAIL and ADMIN_PASSWORD as
    environment variables on the server (see auth_utils.ensure_admin_from_env).
    That prevents every deployment of this codebase from sharing the same
    predictable, publicly-documented admin login.
    """
    admin = ensure_admin_from_env(db)
    if admin:
        return {
            "status": "success",
            "message": f"✅ Admin account ready: {admin.email}",
            "next": "Login at /api/auth/login with the ADMIN_EMAIL/ADMIN_PASSWORD you configured",
        }

    if db.query(models.User).filter(models.User.role == models.UserRole.admin).first():
        return {
            "status": "already_exists",
            "message": "An admin account already exists. Login at /api/auth/login.",
        }

    raise HTTPException(
        status_code=400,
        detail=(
            "No admin account exists yet. Set ADMIN_EMAIL and ADMIN_PASSWORD "
            "(min 8 characters) as environment variables on the server and "
            "call this endpoint again — or restart the app, which runs the "
            "same check automatically on startup."
        ),
    )
