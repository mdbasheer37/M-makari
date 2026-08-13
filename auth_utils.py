import warnings
import os
import secrets

# Suppress passlib bcrypt version warning (harmless with bcrypt==4.0.1)
warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
import models

IS_PRODUCTION = os.getenv("ENVIRONMENT", "production") == "production"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if IS_PRODUCTION:
        # Fail safe: never allow a predictable/shared secret in production.
        raise RuntimeError(
            "SECRET_KEY environment variable is not set.\n"
            "Go to Render → your web service → Environment → add SECRET_KEY "
            "(generate one with: python -c \"import secrets; print(secrets.token_hex(32))\")"
        )
    # Local/dev convenience only — a fresh random key each process start.
    # Tokens will not survive a restart, which is fine for local development.
    SECRET_KEY = secrets.token_hex(32)
    print("⚠️  SECRET_KEY not set — using a temporary random key for this dev session only.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # Truncate to 72 bytes — bcrypt hard limit
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(password_bytes)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> models.User:
    payload = verify_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def get_current_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role not in [models.UserRole.admin, models.UserRole.moderator]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def ensure_admin_from_env(db: Session):
    """
    Create the first admin account from environment variables, if configured.

    Safe/idempotent: does nothing if ADMIN_EMAIL/ADMIN_PASSWORD are not set,
    and does nothing if a user with that email already exists. This replaces
    the old behaviour of auto-creating a well-known "admin123" account, which
    made every deployment of this codebase share the same predictable
    administrator credentials until the owner remembered to change them.

    Returns the created/existing admin User, or None if not configured.
    """
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return None

    existing = db.query(models.User).filter(models.User.email == admin_email.lower()).first()
    if existing:
        return existing

    if len(admin_password) < 8:
        print("⚠️  ADMIN_PASSWORD is too short (min 8 chars) — skipping admin creation.")
        return None

    admin = models.User(
        username=os.getenv("ADMIN_USERNAME", "admin"),
        email=admin_email.lower(),
        full_name=os.getenv("ADMIN_FULL_NAME", "Administrator"),
        hashed_password=get_password_hash(admin_password),
        role=models.UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    print(f"✅ Admin account created from ADMIN_EMAIL/ADMIN_PASSWORD: {admin_email}")
    return admin


VALID_ROLES = {"user", "admin", "moderator"}


def get_optional_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.User | None:
    if not credentials:
        return None
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id:
            return db.query(models.User).filter(models.User.id == int(user_id)).first()
    except Exception:
        pass
    return None
