# ═══════════════════════════════════════════════════════════════
# Project 02 — Auth & RBAC · auth.py
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Core authentication and authorization engine.
#   - SQLite database via SQLAlchemy (users table)
#   - Role-based access control: admin > developer > viewer
#   - JWT token creation + verification (python-jose)
#   - Password hashing with bcrypt (passlib)
#   - API key generation stored as hash (uuid4-based)
#   - FastAPI Depends()-compatible get_current_user function
#
# HOW TO USE:
#   Import into main.py:
#     from auth import get_current_user, require_role, create_user
#
# ROLES & PERMISSIONS:
#   admin     → all endpoints
#   developer → /chat, /models, /chat/stream
#   viewer    → /chat, /chat/stream only
# ═══════════════════════════════════════════════════════════════

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ─────────────────────────────────────────────────────────────
# Config — secrets and DB path from environment
# SECRET_KEY must be changed in production; the default is only
# safe for local development.
# ─────────────────────────────────────────────────────────────

SECRET_KEY     = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM      = "HS256"
TOKEN_EXPIRE_H = 24          # JWT lifetime in hours

# SQLite file sits beside the running process (auto-created)
DB_PATH = os.getenv("DB_PATH", "./auth.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ─────────────────────────────────────────────────────────────
# Role permission matrix
# Centralising this here means a single edit propagates to all
# require_role() calls in main.py automatically.
# ─────────────────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin":     {"chat", "models", "stats", "admin"},
    "developer": {"chat", "models"},
    "viewer":    {"chat"},
}

ALL_ROLES = list(ROLE_PERMISSIONS.keys())


# ═══════════════════════════════════════════════════════════════
# DATABASE SETUP
# ═══════════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    pass


class User(Base):
    """ORM model for the users table.

    api_key_hash stores a SHA-256 digest of the raw API key so
    we never persist the plaintext key — same principle as passwords.
    """
    __tablename__ = "users"

    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username       = Column(String, unique=True, nullable=False, index=True)
    email          = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role           = Column(String, nullable=False, default="viewer")
    api_key_hash   = Column(String, nullable=True)   # nullable until user generates a key
    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active      = Column(Boolean, default=True)


# connect_args disables SQLite's same-thread check so FastAPI's
# async request threads can share the session factory
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create tables and seed the default admin account.

    Called once at application startup. Idempotent — safe to call
    multiple times because create_all() skips existing tables.
    """
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if db.query(User).count() == 0:
            # Seed admin so the system is immediately usable after deploy
            admin = create_user(
                db,
                username="admin",
                email="admin@localhost",
                password="admin123",
                role="admin",
            )
            print(f"[auth] Default admin created (id={admin.id})")


def get_db():
    """FastAPI dependency that yields a scoped DB session.

    Using a generator + try/finally guarantees the session is
    closed even if an exception bubbles up mid-request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# PASSWORD HASHING
# ═══════════════════════════════════════════════════════════════

# CryptContext handles algorithm upgrades automatically — if we
# ever switch from bcrypt, deprecated=auto re-hashes on next login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─────────────────────────────────────────────────────────────
# API key helpers (SHA-256 digest, not bcrypt — keys are long
# random strings so a fast hash is fine and avoids bcrypt's
# per-call cost on every authenticated API request)
# ─────────────────────────────────────────────────────────────

def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════
# JWT TOKENS
# ═══════════════════════════════════════════════════════════════

class TokenData(BaseModel):
    username: str
    role: str
    user_id: str


def create_access_token(data: dict) -> str:
    """Mint a signed JWT that expires in TOKEN_EXPIRE_H hours.

    We embed username + role so downstream handlers can make
    authorization decisions without an extra DB query.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_H)
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData:
    """Decode and validate a JWT, returning the embedded claims.

    Raises HTTP 401 on any failure so callers never see raw jose
    exceptions — consistent error surface for API clients.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub", "")
        role: str     = payload.get("role", "")
        user_id: str  = payload.get("user_id", "")
        if not username:
            raise credentials_exc
        return TokenData(username=username, role=role, user_id=user_id)
    except JWTError:
        raise credentials_exc


# ═══════════════════════════════════════════════════════════════
# USER CRUD
# ═══════════════════════════════════════════════════════════════

def create_user(db: Session, username: str, email: str, password: str, role: str = "viewer") -> User:
    """Insert a new user row, raising 400 if username/email clash."""
    if role not in ALL_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role '{role}'. Choose from {ALL_ROLES}")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Return the User if credentials are valid, else None.

    Returning None (rather than raising) lets the caller decide
    whether to raise 401 or do something else.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_api_key(db: Session, user: User) -> str:
    """Generate a new API key, persist its hash, return the raw value.

    The raw key is shown ONCE — we only store the hash, so if the
    user loses it they must regenerate.
    """
    raw_key = f"ak_{uuid.uuid4().hex}{uuid.uuid4().hex}"   # 66-char prefix + 64 hex chars
    user.api_key_hash = _hash_api_key(raw_key)
    db.commit()
    return raw_key


def get_user_by_api_key(db: Session, raw_key: str) -> Optional[User]:
    """Look up a user by comparing the provided key's hash."""
    key_hash = _hash_api_key(raw_key)
    return (
        db.query(User)
        .filter(User.api_key_hash == key_hash, User.is_active == True)  # noqa: E712
        .first()
    )


# ═══════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCY INJECTION
# ═══════════════════════════════════════════════════════════════

# Two security schemes so clients can choose either
bearer_scheme  = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str]                              = Security(api_key_header),
    db: Session                                         = Depends(get_db),
) -> User:
    """Resolve the caller's identity from Bearer token OR X-API-Key.

    FastAPI calls this via Depends() on every protected endpoint.
    Priority: Bearer token first, then API key — the order matters
    because a request might include both headers by mistake.
    """
    # ── Try JWT Bearer token ──────────────────────────────────
    if credentials and credentials.credentials:
        token_data = verify_token(credentials.credentials)
        user = db.query(User).filter(User.username == token_data.username).first()
        if user and user.is_active:
            return user

    # ── Try X-API-Key header ──────────────────────────────────
    if api_key:
        user = get_user_by_api_key(db, api_key)
        if user:
            return user

    # Neither credential worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide a Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(*required_permissions: str):
    """Dependency factory that enforces role-based access.

    Usage in a route:
        @app.get("/stats", dependencies=[Depends(require_role("stats"))])

    Or as a parameter (when you also need the user object):
        async def stats(user: User = Depends(require_role("stats"))):

    Returns the current user so the route handler can use it.
    """
    def checker(current_user: User = Depends(get_current_user)) -> User:
        user_perms = ROLE_PERMISSIONS.get(current_user.role, set())
        if not any(perm in user_perms for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current_user.role}' cannot access this endpoint. "
                    f"Required: {list(required_permissions)}"
                ),
            )
        return current_user
    return checker
