from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get DATABASE_URL from environment
# Render PostgreSQL gives "postgres://" — SQLAlchemy needs "postgresql://"
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set.\n"
        "Set it in Render → Environment → DATABASE_URL"
    )

# Fix Render's legacy postgres:// prefix
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# PostgreSQL engine — connection pooling tuned for Render free tier
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Test connections before using them
    pool_size=5,               # Max persistent connections
    max_overflow=10,           # Extra connections allowed under load
    pool_recycle=300,          # Recycle connections every 5 minutes
    pool_timeout=30,           # Wait up to 30s for a connection
    echo=os.getenv("ENVIRONMENT") != "production",  # SQL logging in dev only
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection():
    """Test the database connection — called on startup."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL connected successfully")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
