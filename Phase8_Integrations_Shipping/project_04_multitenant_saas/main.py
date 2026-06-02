"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║         Phase 8 — Integrations & Shipping | Project 04: Multi-Tenant SaaS      ║
║                          main.py — FastAPI Multi-Tenant API                     ║
║                                                                                 ║
║  PURPOSE: Demonstrates production-grade multi-tenancy — the architecture that  ║
║  powers SaaS companies like Slack, GitHub, Stripe, and Notion. Every customer   ║
║  (a "tenant") sees only their own data, even though they share the same         ║
║  database and application code.                                                  ║
║                                                                                 ║
║  MULTI-TENANCY STRATEGY: Row-level isolation                                    ║
║  Every table has a tenant_id foreign key. Every query filters by tenant_id      ║
║  extracted from the JWT. This is the simplest approach — works great with        ║
║  SQLite and PostgreSQL row-level security (RLS).                                 ║
║                                                                                 ║
║  KEY CONCEPTS:                                                                   ║
║  - Tenant: An organization (e.g., "Acme Corp") — the billable unit              ║
║  - User: A person within a tenant (one tenant has many users)                   ║
║  - Plan: The subscription tier (free/pro/enterprise) → sets quota               ║
║  - Quota: Max API calls per month — enforced on every /chat request             ║
║  - JWT: JSON Web Token — carries tenant_id + user role, signed with HS256       ║
║                                                                                 ║
║  TECH: FastAPI, SQLite via SQLAlchemy, python-jose JWT, passlib bcrypt          ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from openai import OpenAI
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# WHY use constants not environment variables here? For clarity in the demo.
# In production: load from os.getenv() + fail fast if missing.
# See Project 06 capstone for the production pattern.
# ═══════════════════════════════════════════════════════════════════════════════

SECRET_KEY = "phase8-multitenant-demo-secret-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours for demo convenience

# Super-admin credentials — in production this comes from a separate auth system
SUPER_ADMIN_TOKEN = "superadmin-dev-token-change-in-production"

# Ollama via OpenAI-compatible client
ollama_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
AI_MODEL = "gemma3:4b"

# Database
DATABASE_URL = "sqlite:///./multitenant.db"

# Plan quotas: requests per month (-1 = unlimited)
PLAN_QUOTAS = {
    "free": 100,
    "pro": 1000,
    "enterprise": -1,  # Unlimited — enterprise pays flat rate
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE SETUP
# SQLAlchemy ORM gives us a clean Python interface to the database.
# WHY ORM vs raw SQL? The ORM prevents SQL injection by construction,
# handles type conversion, and makes relationships explicit in code.
# ═══════════════════════════════════════════════════════════════════════════════

engine = create_engine(
    DATABASE_URL,
    # SQLite-specific: disable same-thread check for FastAPI's async handling
    connect_args={"check_same_thread": False},
    echo=False,  # Set to True to see every SQL query in logs
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    DeclarativeBase (SQLAlchemy 2.0+) replaces the older declarative_base()
    function. It provides better type hints and IDE support.
    """
    pass


class TenantModel(Base):
    """Represents an organization/company using our SaaS.

    WHY 'slug'? A URL-safe identifier (e.g., "acme-corp") for tenant-specific
    URLs like "acme-corp.yoursaas.com". The name is display-only.
    """
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    plan = Column(String, default="free")  # free | pro | enterprise
    monthly_quota = Column(Integer, default=100)  # from PLAN_QUOTAS
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserModel(Base):
    """A user account, scoped to a specific tenant.

    WHY tenant_id on users? This is row-level multi-tenancy in action.
    A user in "Acme Corp" cannot access "Startup Inc" data because
    every query is filtered by the tenant_id from their JWT.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # user | admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageLogModel(Base):
    """Records every API call for quota enforcement and billing.

    WHY log every request? We need to:
    1. Enforce monthly quotas (count rows WHERE tenant_id=X AND month=current)
    2. Generate invoices (sum tokens per model per tenant)
    3. Provide usage analytics (/usage endpoint)
    4. Debug unexpected usage spikes

    This table grows fast in production — you'd add a TTL or partition by month.
    """
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)  # e.g. "/chat"
    model = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# Create all tables
Base.metadata.create_all(bind=engine)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# Pydantic models define the shape of API request/response bodies.
# They give us free validation, serialization, and OpenAPI docs.
# ═══════════════════════════════════════════════════════════════════════════════

class TenantCreate(BaseModel):
    name: str
    slug: str
    plan: str = "free"  # Default new tenants to free tier


class TenantOut(BaseModel):
    id: int
    name: str
    slug: str
    plan: str
    monthly_quota: int
    created_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode (SQLAlchemy → Pydantic)


class UserRegister(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: int
    tenant_name: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    model: str
    tenant_id: int
    remaining_quota: Optional[int]  # None for enterprise (unlimited)


class UsageStats(BaseModel):
    tenant_id: int
    tenant_name: str
    plan: str
    monthly_quota: int
    used_this_month: int
    remaining: Optional[int]  # None = unlimited
    usage_by_day: dict[str, int]


class TenantWithUsage(BaseModel):
    id: int
    name: str
    slug: str
    plan: str
    monthly_quota: int
    used_this_month: int
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

# bcrypt for password hashing — the industry standard
# WHY bcrypt? It's intentionally slow, making brute-force attacks impractical.
# Unlike SHA-256 (fast), bcrypt takes ~100ms — fine for login, brutal for attackers.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt. NEVER store plain-text passwords."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_jwt(user_id: int, tenant_id: int, email: str, role: str) -> str:
    """Create a JWT token encoding the user's identity and tenant scope.

    WHY put tenant_id in the JWT? Every API request needs to know which tenant
    it belongs to. By embedding it in the JWT, we avoid a database lookup
    on every request just to get the tenant_id.

    The token is signed with HS256 — any tampering invalidates the signature.
    This is why we never store JWTs server-side — validation is cryptographic.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),       # Subject: the user ID
        "tenant_id": tenant_id,    # Multi-tenancy: which org this user belongs to
        "email": email,
        "role": role,              # "user" or "admin"
        "exp": expire,             # Expiration timestamp
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT token. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# FastAPI's dependency injection system lets us share logic across endpoints.
# These functions run before the endpoint handler and inject validated data.
# ═══════════════════════════════════════════════════════════════════════════════

def get_db() -> Session:
    """Provide a SQLAlchemy database session.

    WHY use a generator? The 'finally' block guarantees the session is
    closed even if the endpoint raises an exception. Without this,
    connections would leak and the app would eventually hang.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Extract and validate the current user from the JWT Bearer token.

    This is injected into every protected endpoint. The user dict contains:
    - user_id, tenant_id, email, role
    - The full user DB record for convenience
    """
    payload = decode_jwt(credentials.credentials)

    user_id = int(payload["sub"])
    tenant_id = payload["tenant_id"]

    # Verify the user still exists and belongs to the claimed tenant
    user = db.query(UserModel).filter(
        UserModel.id == user_id,
        UserModel.tenant_id == tenant_id,
        UserModel.is_active == True,
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "email": payload["email"],
        "role": payload["role"],
        "user": user,
    }


def require_super_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> None:
    """Restrict an endpoint to the super-admin only.

    WHY a separate super-admin token (not a user role)? Super-admin actions
    (creating tenants, listing all tenants) are infrastructure-level operations.
    They don't belong to any tenant, so they can't use a tenant-scoped JWT.
    In production, this would be an internal API key stored in a secrets manager.
    """
    if credentials.credentials != SUPER_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Super-admin access required")


def enforce_quota(
    tenant_id: int,
    tenant: TenantModel,
    db: Session,
) -> int:
    """Check if the tenant has remaining quota for this month.

    Returns the current month usage count.
    Raises HTTP 429 (Too Many Requests) if quota is exceeded.

    WHY 429 and not 403? HTTP semantics matter:
    - 403 = Forbidden (you don't have permission)
    - 429 = Rate limited (you exceeded your quota, try later or upgrade)
    """
    if tenant.monthly_quota == -1:
        return 0  # Enterprise: unlimited

    # Count requests this calendar month for this tenant
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    used = db.query(func.count(UsageLogModel.id)).filter(
        UsageLogModel.tenant_id == tenant_id,
        UsageLogModel.timestamp >= month_start,
    ).scalar() or 0

    if used >= tenant.monthly_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly quota exceeded. Used {used}/{tenant.monthly_quota} requests. "
                f"Upgrade to a higher plan at /billing."
            ),
        )

    return used


# ═══════════════════════════════════════════════════════════════════════════════
# APP STARTUP — SEED DEMO TENANTS
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Seed demo tenants and admin users on startup."""
    seed_demo_data()
    yield  # App runs here
    # Cleanup on shutdown (nothing needed for SQLite demo)


def seed_demo_data() -> None:
    """Create 3 demo tenants with admin users if they don't exist.

    WHY seed on startup? This makes the demo immediately runnable — no
    manual setup steps. In production, tenants are created via the
    POST /tenants endpoint by your sales/ops team.
    """
    db = SessionLocal()
    try:
        demo_tenants = [
            {
                "name": "Acme Corp",
                "slug": "acme-corp",
                "plan": "pro",
                "quota": PLAN_QUOTAS["pro"],
                "admin_email": "admin@acme-corp.example",
                "admin_password": "acme-admin-pass",
            },
            {
                "name": "Startup Inc",
                "slug": "startup-inc",
                "plan": "free",
                "quota": PLAN_QUOTAS["free"],
                "admin_email": "admin@startup-inc.example",
                "admin_password": "startup-admin-pass",
            },
            {
                "name": "BigCorp Enterprise",
                "slug": "bigcorp",
                "plan": "enterprise",
                "quota": PLAN_QUOTAS["enterprise"],
                "admin_email": "admin@bigcorp.example",
                "admin_password": "bigcorp-admin-pass",
            },
        ]

        for td in demo_tenants:
            # Check if tenant already exists (idempotent seed)
            existing = db.query(TenantModel).filter(
                TenantModel.slug == td["slug"]
            ).first()

            if not existing:
                tenant = TenantModel(
                    name=td["name"],
                    slug=td["slug"],
                    plan=td["plan"],
                    monthly_quota=td["quota"],
                )
                db.add(tenant)
                db.flush()  # Get the tenant.id before creating the user

                # Create an admin user for this tenant
                admin = UserModel(
                    tenant_id=tenant.id,
                    email=td["admin_email"],
                    hashed_password=hash_password(td["admin_password"]),
                    role="admin",
                )
                db.add(admin)

        db.commit()
        print("✓ Demo tenants seeded (acme-corp/pro, startup-inc/free, bigcorp/enterprise)")

    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Multi-Tenant SaaS API — Phase 8 Project 04",
    description="""
    A multi-tenant SaaS API demonstrating:
    - **Row-level tenant isolation** — every query filters by tenant_id
    - **JWT-based auth** — tenant_id embedded in token
    - **Usage quota enforcement** — plan limits enforced on /chat
    - **Super-admin** — manage all tenants across the platform
    """,
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Simple health check — used by load balancers and monitoring."""
    return {"status": "healthy", "service": "multitenant-saas", "version": "1.0.0"}


# ─── Tenant Management (Super-Admin Only) ─────────────────────────────────────

@app.post(
    "/tenants",
    response_model=TenantOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Super-Admin"],
    summary="Create a new tenant organization",
)
def create_tenant(
    body: TenantCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_super_admin),
):
    """Create a new tenant (organization) in the platform.

    Only callable with the super-admin token. In a real product, this is
    called by your sales team when closing a new customer deal.
    """
    # Check slug uniqueness — slugs are used in URLs so must be unique globally
    existing = db.query(TenantModel).filter(TenantModel.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Slug '{body.slug}' already taken")

    if body.plan not in PLAN_QUOTAS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {list(PLAN_QUOTAS)}")

    tenant = TenantModel(
        name=body.name,
        slug=body.slug,
        plan=body.plan,
        monthly_quota=PLAN_QUOTAS[body.plan],
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@app.get(
    "/admin/tenants",
    tags=["Super-Admin"],
    summary="List all tenants with usage stats",
)
def list_all_tenants(
    db: Session = Depends(get_db),
    _: None = Depends(require_super_admin),
):
    """List all tenants with their current month usage.

    Super-admin only — this crosses tenant boundaries intentionally.
    Regular users can only see their own tenant via GET /tenants/me.
    """
    tenants = db.query(TenantModel).all()
    result = []

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for tenant in tenants:
        used = db.query(func.count(UsageLogModel.id)).filter(
            UsageLogModel.tenant_id == tenant.id,
            UsageLogModel.timestamp >= month_start,
        ).scalar() or 0

        result.append(TenantWithUsage(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            plan=tenant.plan,
            monthly_quota=tenant.monthly_quota,
            used_this_month=used,
            created_at=tenant.created_at,
        ))

    return result


# ─── Current Tenant Info ──────────────────────────────────────────────────────

@app.get(
    "/tenants/me",
    response_model=UsageStats,
    tags=["Tenant"],
    summary="Get current tenant info and usage statistics",
)
def get_my_tenant(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current tenant's info and usage stats.

    Uses tenant_id from JWT — users can only see their own tenant.
    This is the tenant isolation guarantee in action.
    """
    tenant_id = current_user["tenant_id"]
    tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total usage this month
    used = db.query(func.count(UsageLogModel.id)).filter(
        UsageLogModel.tenant_id == tenant_id,
        UsageLogModel.timestamp >= month_start,
    ).scalar() or 0

    # Daily breakdown for usage chart
    usage_logs = db.query(UsageLogModel).filter(
        UsageLogModel.tenant_id == tenant_id,
        UsageLogModel.timestamp >= month_start,
    ).all()

    usage_by_day: dict[str, int] = {}
    for log in usage_logs:
        day_key = log.timestamp.strftime("%Y-%m-%d")
        usage_by_day[day_key] = usage_by_day.get(day_key, 0) + 1

    remaining = None if tenant.monthly_quota == -1 else max(0, tenant.monthly_quota - used)

    return UsageStats(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        plan=tenant.plan,
        monthly_quota=tenant.monthly_quota,
        used_this_month=used,
        remaining=remaining,
        usage_by_day=usage_by_day,
    )


# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@app.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED,
    tags=["Auth"],
    summary="Register a new user under the current tenant",
)
def register_user(
    body: UserRegister,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new user under the current tenant.

    WHY require authentication to register? This prevents anyone from creating
    accounts in your tenant. Only existing admins can add new users.
    In a real product, you'd also have a public registration flow that
    creates a new tenant + first user in one step.
    """
    tenant_id = current_user["tenant_id"]

    # Check email uniqueness within this tenant
    # WHY only within this tenant? A user@gmail.com can exist in multiple tenants.
    # Global email uniqueness would break tenant isolation.
    existing = db.query(UserModel).filter(
        UserModel.tenant_id == tenant_id,
        UserModel.email == body.email,
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered in this tenant")

    user = UserModel(
        tenant_id=tenant_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User registered successfully", "user_id": user.id, "tenant_id": tenant_id}


@app.post(
    "/auth/login",
    response_model=TokenOut,
    tags=["Auth"],
    summary="Login and receive a tenant-scoped JWT",
)
def login_user(
    body: UserLogin,
    db: Session = Depends(get_db),
):
    """Login and receive a JWT token scoped to the user's tenant.

    The returned JWT contains tenant_id — every subsequent request uses
    this to enforce data isolation without another database lookup.

    WHY not put the slug in the login URL (e.g., /auth/acme-corp/login)?
    Tenant-in-URL is one valid approach. We use email-based lookup for
    simplicity — in production you'd likely do both.
    """
    # Find user by email across all tenants
    # Note: multiple tenants can have the same email, so we return the first match.
    # In production: require tenant slug in the login request for unambiguous lookup.
    user = db.query(UserModel).filter(
        UserModel.email == body.email,
        UserModel.is_active == True,
    ).first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get the tenant for the response
    tenant = db.query(TenantModel).filter(TenantModel.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=500, detail="Tenant not found for user")

    token = create_jwt(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
    )

    return TokenOut(
        access_token=token,
        tenant_id=user.tenant_id,
        tenant_name=tenant.name,
    )


# ─── AI Chat (Quota-Enforced) ─────────────────────────────────────────────────

@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["AI"],
    summary="Send a message to the AI (quota enforced)",
)
def chat(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI chat endpoint with per-tenant quota enforcement.

    This is the core "metered feature" — every call:
    1. Verifies the user's tenant has remaining quota
    2. Calls the LLM
    3. Logs the usage (for billing + quota tracking)

    WHY log AFTER the LLM call? We want to log successful requests.
    If the LLM fails, we don't charge the quota. In production you'd
    add a pending/confirmed status to handle partial failures.
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]

    # Get the tenant (needed for quota check)
    tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=500, detail="Tenant configuration error")

    # Enforce quota BEFORE calling the LLM (don't waste compute on over-quota tenants)
    used = enforce_quota(tenant_id, tenant, db)

    # Call the LLM
    try:
        response = ollama_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a helpful AI assistant for {tenant.name}. "
                        f"Be concise and helpful."
                    ),
                },
                {"role": "user", "content": body.message},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()

        # Estimate token usage (real Ollama response includes usage stats)
        input_tokens = len(body.message.split()) * 4 // 3  # rough approximation
        output_tokens = len(reply.split()) * 4 // 3

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")

    # Log the usage (this is what enables billing and quota tracking)
    log_entry = UsageLogModel(
        tenant_id=tenant_id,
        user_id=user_id,
        endpoint="/chat",
        model=AI_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    db.add(log_entry)
    db.commit()

    # Calculate remaining quota for the response
    remaining = None  # Unlimited for enterprise
    if tenant.monthly_quota != -1:
        remaining = max(0, tenant.monthly_quota - used - 1)

    return ChatResponse(
        reply=reply,
        model=AI_MODEL,
        tenant_id=tenant_id,
        remaining_quota=remaining,
    )


# ─── Usage Statistics ─────────────────────────────────────────────────────────

@app.get(
    "/usage",
    tags=["Tenant"],
    summary="Get current tenant's usage statistics for this month",
)
def get_usage(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detailed usage statistics for the current tenant.

    This is the data behind a "Usage" page in the SaaS dashboard.
    Tenants can only see their own usage — isolation enforced by JWT.
    """
    tenant_id = current_user["tenant_id"]
    tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    logs = db.query(UsageLogModel).filter(
        UsageLogModel.tenant_id == tenant_id,
        UsageLogModel.timestamp >= month_start,
    ).all()

    # Aggregate by endpoint and by day
    by_endpoint: dict[str, int] = {}
    by_day: dict[str, int] = {}

    for log in logs:
        by_endpoint[log.endpoint] = by_endpoint.get(log.endpoint, 0) + 1
        day = log.timestamp.strftime("%Y-%m-%d")
        by_day[day] = by_day.get(day, 0) + 1

    used = len(logs)
    remaining = None if tenant.monthly_quota == -1 else max(0, tenant.monthly_quota - used)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.name,
        "plan": tenant.plan,
        "month": now.strftime("%B %Y"),
        "monthly_quota": tenant.monthly_quota if tenant.monthly_quota != -1 else "unlimited",
        "used": used,
        "remaining": remaining if remaining is not None else "unlimited",
        "by_endpoint": by_endpoint,
        "by_day": by_day,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# Run with: uvicorn main:app --reload --port 8000
# Docs at: http://localhost:8000/docs
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
