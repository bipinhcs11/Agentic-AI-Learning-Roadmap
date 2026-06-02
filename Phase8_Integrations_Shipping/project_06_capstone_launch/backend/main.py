"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║  Phase 8 — Integrations & Shipping | Project 06: Capstone — AskMyDocs Pro      ║
║                    backend/main.py — Complete FastAPI Backend                   ║
║                                                                                 ║
║  PURPOSE: A production-grade, launch-ready AI SaaS backend combining:           ║
║  ✦ Multi-tenant auth (Project 04 pattern)                                       ║
║  ✦ Document upload + RAG pipeline (Phase 6 DocuMind pattern)                   ║
║  ✦ Usage metering + billing (Project 05 pattern)                                ║
║  ✦ WebSocket streaming chat (Phase 7 Project 02 pattern)                        ║
║  ✦ Slack webhook receiver for /ask command                                      ║
║  ✦ Full health check + metrics endpoint                                         ║
║                                                                                 ║
║  PRODUCT: AskMyDocs Pro                                                         ║
║  Upload your documents → Ask questions in natural language → Get AI answers     ║
║  grounded in YOUR data, with citations, multi-tenant isolation, and billing.    ║
║                                                                                 ║
║  ARCHITECTURE LAYERS:                                                           ║
║    HTTP Layer:   FastAPI routes + middleware (auth, metering, CORS)             ║
║    WebSocket:    Real-time streaming chat (SSE-over-WS pattern)                 ║
║    RAG Layer:    PDF ingestion → chunking → embedding → vector search           ║
║    LLM Layer:    Ollama via OpenAI client (swap for GPT-4 with one env change)  ║
║    Data Layer:   SQLite (swap for PostgreSQL for production scale)              ║
║                                                                                 ║
║  ENV VARS (all have safe defaults for local dev):                               ║
║    SECRET_KEY          JWT signing secret                                       ║
║    OLLAMA_BASE_URL     Ollama endpoint (default: http://localhost:11434/v1)     ║
║    AI_MODEL            LLM model name (default: gemma3:4b)                      ║
║    DATABASE_URL        SQLAlchemy URL (default: sqlite:///./askmydocs.db)       ║
║    SLACK_SIGNING_SECRET Slack webhook signature verification                    ║
║    SUPER_ADMIN_TOKEN   Admin API key                                            ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import json
import logging
import math
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx
import numpy as np
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from openai import OpenAI
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# PDF parsing — graceful fallback if pypdf not installed
try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("pypdf not installed — PDF upload will be disabled. pip install pypdf")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("askmydocs")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION — All from environment variables with safe dev defaults
# WHY env vars? The 12-Factor App methodology: config belongs in the environment,
# not in the code. This makes deployment to different environments (dev/staging/prod)
# a matter of setting env vars, not changing code.
# ═══════════════════════════════════════════════════════════════════════════════

SECRET_KEY = os.getenv("SECRET_KEY", "askmydocs-dev-secret-CHANGE-IN-PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
SUPER_ADMIN_TOKEN = os.getenv("SUPER_ADMIN_TOKEN", "superadmin-dev-token-CHANGE-IN-PRODUCTION")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "slack-dev-secret")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./askmydocs.db")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
AI_MODEL = os.getenv("AI_MODEL", "gemma3:4b")

# Embedding dimensions depend on the model. nomic-embed-text = 768.
# We use a simple in-process vector store (NumPy) for demo.
# Production: use pgvector, Pinecone, Weaviate, or Qdrant.
EMBEDDING_DIMENSIONS = 768
CHUNK_SIZE = 500   # Characters per document chunk
CHUNK_OVERLAP = 50  # Characters of overlap between chunks

# Plan quotas (requests per month)
PLAN_QUOTAS = {"free": 50, "pro": 500, "enterprise": -1}

# ─── Clients ──────────────────────────────────────────────────────────────────
ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE — SQLAlchemy Models
# ═══════════════════════════════════════════════════════════════════════════════

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class TenantModel(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    plan = Column(String, default="free")
    monthly_quota = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentModel(Base):
    """Stores uploaded document metadata.

    WHY not store the file in the DB? Large binary files in SQLite degrade
    performance. We store only metadata here; actual content lives in chunks.
    In production: store files in S3, metadata in the DB.
    """
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    content_type = Column(String)
    char_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="processing")  # processing | ready | failed
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentChunkModel(Base):
    """One chunk of a document with its embedding stored as JSON.

    WHY chunk documents? LLMs have context limits. A 100-page PDF can't fit
    in a single prompt. Chunking + retrieval solves this:
    1. Split document into overlapping chunks (~500 chars each)
    2. Embed each chunk into a vector
    3. At query time: embed the query, find most similar chunks
    4. Send only the top-K relevant chunks to the LLM
    This is the RAG (Retrieval-Augmented Generation) pattern.
    """
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text)  # JSON array of floats — the semantic fingerprint
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageLogModel(Base):
    __tablename__ = "usage_logs"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)
    model = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


Base.metadata.create_all(bind=engine)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class TenantCreate(BaseModel):
    name: str
    slug: str
    plan: str = "free"


class UserRegister(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    document_id: Optional[int] = None  # If provided, search only this document
    top_k: int = 3  # How many chunks to retrieve


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]  # [{document_id, filename, chunk_excerpt}]
    model: str
    remaining_quota: Optional[int]


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY
# ═══════════════════════════════════════════════════════════════════════════════

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_jwt(user_id: int, tenant_id: int, email: str, role: str) -> str:
    """Create a tenant-scoped JWT. See Project 04 for detailed explanation."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "tenant_id": tenant_id, "email": email, "role": role, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Validate JWT and return current user context."""
    payload = decode_jwt(credentials.credentials)
    user_id = int(payload["sub"])
    tenant_id = payload["tenant_id"]

    user = db.query(UserModel).filter(
        UserModel.id == user_id,
        UserModel.tenant_id == tenant_id,
        UserModel.is_active == True,
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "email": payload["email"],
        "role": payload["role"],
    }


def require_super_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.credentials != SUPER_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Super-admin access required")


def get_tenant_and_enforce_quota(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[dict, TenantModel]:
    """Combined dependency: get user + verify tenant quota.

    WHY combine these? Every protected AI endpoint needs both the user context
    AND the quota check. Combining into one dependency keeps endpoint code clean
    and ensures we never forget to check quota on a new endpoint.
    """
    tenant_id = current_user["tenant_id"]
    tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=500, detail="Tenant configuration error")

    if tenant.monthly_quota != -1:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        used = db.query(func.count(UsageLogModel.id)).filter(
            UsageLogModel.tenant_id == tenant_id,
            UsageLogModel.timestamp >= month_start,
        ).scalar() or 0

        if used >= tenant.monthly_quota:
            raise HTTPException(
                status_code=429,
                detail=f"Monthly quota exceeded ({used}/{tenant.monthly_quota}). Please upgrade your plan.",
            )

    return current_user, tenant


# ═══════════════════════════════════════════════════════════════════════════════
# RAG ENGINE — Document processing and retrieval
# ═══════════════════════════════════════════════════════════════════════════════

class RAGEngine:
    """Retrieval-Augmented Generation engine.

    WHY RAG? Base LLMs don't know about YOUR documents. RAG solves this by:
    1. Pre-processing: split docs → embed chunks → store vectors
    2. At query time: embed query → find similar chunks → send to LLM as context

    The LLM then answers based on your documents, not its training data.
    This is how ChatGPT plugins, GitHub Copilot Chat, and Notion AI work.

    EMBEDDING MODEL: nomic-embed-text via Ollama
    Why Ollama for embeddings? Free, local, no API key needed.
    Production alternatives: OpenAI text-embedding-3-small, Cohere embed-v3.

    VECTOR SIMILARITY: Cosine similarity (NumPy)
    Why cosine? It measures the angle between vectors, not their magnitude.
    Two sentences about "database performance" will have similar directions
    even if one is 10 words and one is 100 words.
    """

    EMBEDDING_MODEL = "nomic-embed-text"  # Run: ollama pull nomic-embed-text

    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks.

        WHY overlap? If a key sentence is at a chunk boundary, we'd miss half
        of it in retrieval. Overlap ensures every sentence appears fully in
        at least one chunk.

        BETTER APPROACHES for production:
        - Semantic chunking: split at sentence/paragraph boundaries
        - Recursive character splitting: try paragraph → sentence → word
        - Document-specific: split at headers for markdown, pages for PDFs
        LangChain's RecursiveCharacterTextSplitter implements this well.
        """
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():  # Skip empty chunks
                chunks.append(chunk.strip())
            start = end - CHUNK_OVERLAP  # Overlap with next chunk
        return chunks

    def embed_text(self, text: str) -> list[float]:
        """Create an embedding vector for a piece of text.

        The embedding is a list of ~768 floats representing the semantic
        meaning of the text. Similar texts → similar vectors.

        FALLBACK: If Ollama isn't available or nomic-embed-text isn't installed,
        we use a deterministic hash-based pseudo-embedding. This won't give
        good search results but lets the app run without the model.
        """
        try:
            response = ollama.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding failed (using fallback): {e}")
            # Deterministic fallback: hash text into a pseudo-embedding
            # NOT suitable for production — just keeps the demo working
            text_bytes = text.encode("utf-8")
            pseudo = []
            for i in range(EMBEDDING_DIMENSIONS):
                h = hashlib.md5(f"{text_bytes}_{i}".encode()).digest()
                val = (int.from_bytes(h[:4], "big") / 2**32) - 0.5
                pseudo.append(val)
            return pseudo

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Returns a value between -1 and 1:
        - 1.0 = identical direction (semantically identical)
        - 0.0 = orthogonal (unrelated)
        - -1.0 = opposite direction (semantically opposite)

        For text embeddings, we typically see values between 0.5-0.95
        for related content.
        """
        a_np = np.array(a)
        b_np = np.array(b)
        dot = np.dot(a_np, b_np)
        norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
        if norm == 0:
            return 0.0
        return float(dot / norm)

    def find_relevant_chunks(
        self,
        query: str,
        tenant_id: int,
        document_id: Optional[int],
        top_k: int,
        db: Session,
    ) -> list[dict]:
        """Find the most semantically relevant document chunks for a query.

        This is the 'R' in RAG — Retrieval.

        PRODUCTION SCALING:
        For a few hundred documents: this NumPy approach works fine.
        For thousands of documents: use a vector database (Pinecone, Qdrant,
        pgvector) that indexes vectors for sub-millisecond search at scale.
        """
        # Embed the user's query
        query_embedding = self.embed_text(query)

        # Get all chunks for this tenant (with optional document filter)
        query_filter = [DocumentChunkModel.tenant_id == tenant_id]
        if document_id:
            query_filter.append(DocumentChunkModel.document_id == document_id)

        chunks = db.query(DocumentChunkModel).filter(*query_filter).all()

        if not chunks:
            return []

        # Calculate similarity between query and every chunk
        scored_chunks = []
        for chunk in chunks:
            if not chunk.embedding_json:
                continue
            try:
                chunk_embedding = json.loads(chunk.embedding_json)
                score = self.cosine_similarity(query_embedding, chunk_embedding)
                scored_chunks.append((score, chunk))
            except Exception:
                continue

        # Sort by similarity and return top K
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top = scored_chunks[:top_k]

        return [
            {
                "score": score,
                "content": chunk.content,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
            }
            for score, chunk in top
        ]

    def build_rag_prompt(self, question: str, chunks: list[dict], tenant_name: str) -> str:
        """Build the prompt that gives the LLM context from retrieved chunks.

        This is prompt engineering for RAG. The key elements:
        1. System role: tells the LLM it's a document assistant
        2. Context: the retrieved chunks (grounding for the answer)
        3. Instructions: answer from context, admit uncertainty
        4. Question: the user's actual question

        WHY "only use the provided context"? Without this constraint, the LLM
        will supplement gaps with its training data, which may be wrong or
        irrelevant to your specific documents. We want grounded answers.
        """
        if not chunks:
            return (
                f"You are a helpful assistant for {tenant_name}. "
                f"The user asked: {question}\n\n"
                "Unfortunately, no relevant documents were found. "
                "Please tell the user to upload relevant documents first."
            )

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Document Excerpt {i}]\n{chunk['content']}")

        context = "\n\n".join(context_parts)

        return f"""You are a knowledgeable assistant for {tenant_name} that answers questions based on the provided document excerpts.

CONTEXT FROM DOCUMENTS:
{context}

INSTRUCTIONS:
- Answer the question using ONLY the provided context above
- If the answer isn't in the context, say "I don't have enough information in the uploaded documents to answer this"
- Be concise and accurate
- Quote or reference specific parts of the context when helpful

QUESTION: {question}

ANSWER:"""


# Global RAG engine instance
rag = RAGEngine()


# ═══════════════════════════════════════════════════════════════════════════════
# APP STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Seed demo data on startup."""
    seed_demo_tenants()
    logger.info("AskMyDocs Pro backend started successfully")
    yield
    logger.info("AskMyDocs Pro backend shutting down")


def seed_demo_tenants() -> None:
    """Create 3 demo tenants with admin users."""
    db = SessionLocal()
    try:
        demos = [
            ("Acme Corp", "acme-corp", "pro", "admin@acme.example", "acme-pass-123"),
            ("Startup Inc", "startup-inc", "free", "admin@startup.example", "startup-pass-123"),
            ("BigCorp Enterprise", "bigcorp", "enterprise", "admin@bigcorp.example", "bigcorp-pass-123"),
        ]
        for name, slug, plan, email, password in demos:
            if not db.query(TenantModel).filter(TenantModel.slug == slug).first():
                tenant = TenantModel(
                    name=name, slug=slug, plan=plan, monthly_quota=PLAN_QUOTAS[plan]
                )
                db.add(tenant)
                db.flush()
                db.add(UserModel(
                    tenant_id=tenant.id,
                    email=email,
                    hashed_password=hash_password(password),
                    role="admin",
                ))
        db.commit()
        logger.info("Demo tenants seeded")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="AskMyDocs Pro API",
    description="Multi-tenant document Q&A SaaS with billing, Slack integration, and real-time streaming",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Streamlit frontend and any localhost dev port
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit default port
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health & Metrics ─────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint — called by load balancers every 30 seconds.

    Returns component-level health so ops teams can pinpoint failures:
    - database: can we execute a query?
    - ai: can we reach Ollama?
    """
    # Check database
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    # Check Ollama (non-blocking — we don't fail health if AI is down)
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL.replace('/v1', '')}/api/tags", timeout=2.0)
        ai_status = "healthy" if resp.status_code == 200 else f"unhealthy: {resp.status_code}"
    except Exception as e:
        ai_status = f"unreachable: {e}"

    overall = "healthy" if db_status == "healthy" else "degraded"
    return {
        "status": overall,
        "service": "askmydocs-pro",
        "version": "1.0.0",
        "components": {
            "database": db_status,
            "ai": ai_status,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/metrics", tags=["System"])
def get_metrics(
    db: Session = Depends(get_db),
    _: None = Depends(require_super_admin),
):
    """Platform-wide metrics (super-admin only).

    In production, you'd expose this to Prometheus or send to Grafana.
    """
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return {
        "tenants_total": db.query(func.count(TenantModel.id)).scalar(),
        "users_total": db.query(func.count(UserModel.id)).scalar(),
        "documents_total": db.query(func.count(DocumentModel.id)).scalar(),
        "requests_this_month": db.query(func.count(UsageLogModel.id)).filter(
            UsageLogModel.timestamp >= month_start
        ).scalar(),
        "timestamp": now.isoformat(),
    }


# ─── Tenant Management ────────────────────────────────────────────────────────

@app.post("/tenants", status_code=201, tags=["Admin"])
def create_tenant(
    body: TenantCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_super_admin),
):
    """Create a new tenant (super-admin only)."""
    if db.query(TenantModel).filter(TenantModel.slug == body.slug).first():
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
    return {"id": tenant.id, "name": tenant.name, "slug": tenant.slug, "plan": tenant.plan}


@app.get("/tenants/me", tags=["Tenant"])
def my_tenant(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current tenant info + usage stats."""
    tenant_id = current_user["tenant_id"]
    tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = db.query(func.count(UsageLogModel.id)).filter(
        UsageLogModel.tenant_id == tenant_id,
        UsageLogModel.timestamp >= month_start,
    ).scalar() or 0

    doc_count = db.query(func.count(DocumentModel.id)).filter(
        DocumentModel.tenant_id == tenant_id
    ).scalar() or 0

    remaining = None if tenant.monthly_quota == -1 else max(0, tenant.monthly_quota - used)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "monthly_quota": tenant.monthly_quota if tenant.monthly_quota != -1 else "unlimited",
        "used_this_month": used,
        "remaining": remaining if remaining is not None else "unlimited",
        "document_count": doc_count,
    }


@app.get("/admin/tenants", tags=["Admin"])
def list_tenants(
    db: Session = Depends(get_db),
    _: None = Depends(require_super_admin),
):
    """List all tenants with usage (super-admin only)."""
    tenants = db.query(TenantModel).all()
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = []
    for t in tenants:
        used = db.query(func.count(UsageLogModel.id)).filter(
            UsageLogModel.tenant_id == t.id,
            UsageLogModel.timestamp >= month_start,
        ).scalar() or 0
        result.append({
            "id": t.id, "name": t.name, "slug": t.slug,
            "plan": t.plan, "monthly_quota": t.monthly_quota,
            "used_this_month": used, "created_at": t.created_at.isoformat(),
        })
    return result


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.post("/auth/register", status_code=201, tags=["Auth"])
def register(
    body: UserRegister,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new user under the current tenant (requires existing auth)."""
    tenant_id = current_user["tenant_id"]
    if db.query(UserModel).filter(
        UserModel.tenant_id == tenant_id,
        UserModel.email == body.email,
    ).first():
        raise HTTPException(status_code=400, detail="Email already registered in this tenant")

    user = UserModel(
        tenant_id=tenant_id,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    return {"message": "Registered", "user_id": user.id}


@app.post("/auth/login", tags=["Auth"])
def login(body: UserLogin, db: Session = Depends(get_db)):
    """Login and receive a tenant-scoped JWT."""
    user = db.query(UserModel).filter(
        UserModel.email == body.email,
        UserModel.is_active == True,
    ).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tenant = db.query(TenantModel).filter(TenantModel.id == user.tenant_id).first()
    token = create_jwt(user.id, user.tenant_id, user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant_id": user.tenant_id,
        "tenant_name": tenant.name if tenant else "unknown",
        "role": user.role,
    }


# ─── Document Upload & RAG ────────────────────────────────────────────────────

@app.post("/documents", status_code=201, tags=["Documents"])
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document (PDF or TXT) and index it for RAG.

    Processing pipeline:
    1. Read file bytes
    2. Extract text (PDF via pypdf, TXT directly)
    3. Chunk into overlapping segments
    4. Embed each chunk via nomic-embed-text
    5. Store chunks + embeddings in database

    WHY async? File upload reads can be slow for large files.
    FastAPI's async handling lets other requests continue while we read.
    """
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]

    # Validate file type
    allowed_types = {"text/plain", "application/pdf"}
    content_type = file.content_type or "text/plain"
    if content_type not in allowed_types and not file.filename.endswith((".txt", ".pdf")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")

    # Create document record
    doc = DocumentModel(
        tenant_id=tenant_id,
        user_id=user_id,
        filename=file.filename or "unnamed",
        content_type=content_type,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Extract text
    file_bytes = await file.read()
    text = ""

    try:
        if file.filename and file.filename.endswith(".pdf"):
            if not PDF_SUPPORT:
                raise HTTPException(status_code=400, detail="PDF support requires: pip install pypdf")
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = file_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=422, detail=f"Could not extract text: {e}")

    if not text.strip():
        doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=422, detail="Document appears to be empty or unreadable")

    # Chunk and embed (this is the slow part — in production, run in background task)
    chunks = rag.chunk_text(text)
    logger.info(f"Document {doc.id}: {len(text)} chars → {len(chunks)} chunks")

    for i, chunk_text in enumerate(chunks):
        embedding = rag.embed_text(chunk_text)
        chunk = DocumentChunkModel(
            document_id=doc.id,
            tenant_id=tenant_id,
            chunk_index=i,
            content=chunk_text,
            embedding_json=json.dumps(embedding),
        )
        db.add(chunk)

    # Update document status
    doc.char_count = len(text)
    doc.chunk_count = len(chunks)
    doc.status = "ready"
    db.commit()

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "char_count": doc.char_count,
        "chunk_count": doc.chunk_count,
        "status": "ready",
        "message": f"Document indexed with {len(chunks)} chunks. Ready to query.",
    }


@app.get("/documents", tags=["Documents"])
def list_documents(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents for the current tenant."""
    docs = db.query(DocumentModel).filter(
        DocumentModel.tenant_id == current_user["tenant_id"]
    ).order_by(DocumentModel.created_at.desc()).all()

    return [
        {
            "id": d.id,
            "filename": d.filename,
            "char_count": d.char_count,
            "chunk_count": d.chunk_count,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@app.delete("/documents/{document_id}", tags=["Documents"])
def delete_document(
    document_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document and all its chunks (tenant-scoped)."""
    tenant_id = current_user["tenant_id"]
    doc = db.query(DocumentModel).filter(
        DocumentModel.id == document_id,
        DocumentModel.tenant_id == tenant_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete chunks first (foreign key constraint)
    db.query(DocumentChunkModel).filter(
        DocumentChunkModel.document_id == document_id
    ).delete()
    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.filename}' deleted"}


# ─── AI Chat (HTTP, with RAG) ─────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse, tags=["AI"])
def chat(
    body: ChatRequest,
    deps: tuple = Depends(get_tenant_and_enforce_quota),
    db: Session = Depends(get_db),
):
    """RAG-powered chat — answers questions from uploaded documents.

    This endpoint is the core product. It:
    1. Checks quota (raises 429 if exceeded)
    2. Retrieves relevant document chunks for the question
    3. Builds a grounded prompt with context
    4. Calls the LLM
    5. Logs usage for billing
    6. Returns answer + source citations
    """
    current_user, tenant = deps
    tenant_id = current_user["tenant_id"]

    # Retrieve relevant chunks
    chunks = rag.find_relevant_chunks(
        query=body.message,
        tenant_id=tenant_id,
        document_id=body.document_id,
        top_k=body.top_k,
        db=db,
    )

    # Build RAG prompt and call LLM
    prompt = rag.build_rag_prompt(body.message, chunks, tenant.name)

    try:
        response = ollama.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # Low temperature for factual, grounded answers
            max_tokens=800,
        )
        answer = response.choices[0].message.content.strip()
        input_tokens = len(prompt.split()) * 4 // 3
        output_tokens = len(answer.split()) * 4 // 3
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")

    # Log usage
    cost = (input_tokens / 1000 * 0.0001) + (output_tokens / 1000 * 0.0003)
    db.add(UsageLogModel(
        tenant_id=tenant_id,
        user_id=current_user["user_id"],
        endpoint="/chat",
        model=AI_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    ))
    db.commit()

    # Build source citations for the response
    sources = []
    seen_doc_ids = set()
    for chunk in chunks:
        doc_id = chunk["document_id"]
        if doc_id not in seen_doc_ids:
            doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
            if doc:
                sources.append({
                    "document_id": doc_id,
                    "filename": doc.filename,
                    "chunk_excerpt": chunk["content"][:200] + "...",
                    "relevance_score": round(chunk["score"], 3),
                })
                seen_doc_ids.add(doc_id)

    # Calculate remaining quota
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = db.query(func.count(UsageLogModel.id)).filter(
        UsageLogModel.tenant_id == tenant_id,
        UsageLogModel.timestamp >= month_start,
    ).scalar() or 0
    remaining = None if tenant.monthly_quota == -1 else max(0, tenant.monthly_quota - used)

    return ChatResponse(
        answer=answer,
        sources=sources,
        model=AI_MODEL,
        remaining_quota=remaining,
    )


# ─── WebSocket Streaming Chat ──────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    """Real-time streaming chat via WebSocket.

    WHY WebSocket for streaming?
    HTTP responses wait for the full response before sending.
    WebSocket + streaming LLM lets us send tokens as they're generated,
    giving the user the "thinking in real-time" experience of ChatGPT.

    PROTOCOL:
    Client sends: {"message": "...", "document_id": null}
    Server sends (multiple): {"type": "token", "content": "..."}
    Server sends (final):    {"type": "done", "sources": [...], "remaining_quota": N}
    Server sends (on error): {"type": "error", "message": "..."}

    WHY send token by token? Streaming starts rendering immediately.
    A 500-token response at ~50 tokens/sec feels instant instead of
    making the user wait 10 seconds for the full response.
    """
    await websocket.accept()

    # Authenticate via token query param (WebSocket can't use HTTP headers easily)
    try:
        payload = decode_jwt(token)
        user_id = int(payload["sub"])
        tenant_id = payload["tenant_id"]
        user = db.query(UserModel).filter(
            UserModel.id == user_id,
            UserModel.tenant_id == tenant_id,
            UserModel.is_active == True,
        ).first()
        if not user:
            await websocket.send_json({"type": "error", "message": "Authentication failed"})
            await websocket.close()
            return
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Auth error: {e}"})
        await websocket.close()
        return

    tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()

    try:
        while True:
            # Wait for a message from the client
            data = await websocket.receive_json()
            question = data.get("message", "")
            document_id = data.get("document_id")
            top_k = data.get("top_k", 3)

            if not question:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            # Check quota
            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if tenant and tenant.monthly_quota != -1:
                used = db.query(func.count(UsageLogModel.id)).filter(
                    UsageLogModel.tenant_id == tenant_id,
                    UsageLogModel.timestamp >= month_start,
                ).scalar() or 0
                if used >= tenant.monthly_quota:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Quota exceeded ({used}/{tenant.monthly_quota}). Please upgrade.",
                    })
                    continue

            # Retrieve relevant chunks
            chunks = rag.find_relevant_chunks(
                query=question,
                tenant_id=tenant_id,
                document_id=document_id,
                top_k=top_k,
                db=db,
            )

            prompt = rag.build_rag_prompt(question, chunks, tenant.name if tenant else "AskMyDocs")

            # Stream the LLM response token by token
            try:
                stream = ollama.chat.completions.create(
                    model=AI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=800,
                    stream=True,  # Key: stream=True enables token-by-token delivery
                )

                full_response = ""
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_response += delta
                        # Send each token to the WebSocket client immediately
                        await websocket.send_json({"type": "token", "content": delta})
                        # Small sleep lets the event loop breathe between sends
                        await asyncio.sleep(0)

            except Exception as e:
                await websocket.send_json({"type": "error", "message": f"AI error: {e}"})
                continue

            # Log usage
            input_tokens = len(prompt.split()) * 4 // 3
            output_tokens = len(full_response.split()) * 4 // 3
            cost = (input_tokens / 1000 * 0.0001) + (output_tokens / 1000 * 0.0003)
            db.add(UsageLogModel(
                tenant_id=tenant_id,
                user_id=user_id,
                endpoint="/ws/chat",
                model=AI_MODEL,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            ))
            db.commit()

            # Build sources for the final message
            sources = []
            for c in chunks:
                doc = db.query(DocumentModel).filter(DocumentModel.id == c["document_id"]).first()
                if doc:
                    sources.append({
                        "document_id": c["document_id"],
                        "filename": doc.filename,
                        "relevance_score": round(c["score"], 3),
                    })

            # Count updated usage
            used_after = db.query(func.count(UsageLogModel.id)).filter(
                UsageLogModel.tenant_id == tenant_id,
                UsageLogModel.timestamp >= month_start,
            ).scalar() or 0

            remaining = None if (tenant and tenant.monthly_quota == -1) else max(
                0, (tenant.monthly_quota if tenant else 50) - used_after
            )

            # Send "done" signal with metadata
            await websocket.send_json({
                "type": "done",
                "sources": sources,
                "remaining_quota": remaining,
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")


# ─── Slack Integration ────────────────────────────────────────────────────────

@app.post("/slack/ask", tags=["Integrations"])
async def slack_ask(request: Request, db: Session = Depends(get_db)):
    """Receive Slack slash command /ask and return an AI answer.

    Slack sends a POST with form data when a user types /ask <question>.
    We verify the request signature, find the tenant by Slack team ID,
    and return an answer from their documents.

    HOW TO SET UP (real Slack):
    1. Create a Slack app at api.slack.com/apps
    2. Add a slash command /ask pointing to: https://yourdomain.com/slack/ask
    3. Copy the Signing Secret to SLACK_SIGNING_SECRET env var
    4. Install the app to your workspace

    SECURITY: WHY verify the Slack signature?
    Without verification, anyone can POST to your /slack/ask endpoint
    pretending to be Slack. The signature uses HMAC-SHA256 with your
    Signing Secret, which only you and Slack know.
    """
    body_bytes = await request.body()

    # Verify Slack signature to ensure request is genuine
    # Real Slack sends: X-Slack-Request-Timestamp and X-Slack-Signature headers
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "0")
    slack_signature = request.headers.get("X-Slack-Signature", "")

    # Replay attack protection: reject requests older than 5 minutes
    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=403, detail="Request too old")

    # Verify HMAC signature
    sig_basestring = f"v0:{timestamp}:{body_bytes.decode()}"
    expected_sig = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()

    # In dev mode (no real Slack secret), skip verification
    if SLACK_SIGNING_SECRET != "slack-dev-secret" and not hmac.compare_digest(
        expected_sig, slack_signature
    ):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    # Parse Slack's form data
    # Slack sends: token, team_id, user_id, command, text, response_url
    form_data = {}
    for part in body_bytes.decode().split("&"):
        if "=" in part:
            key, _, value = part.partition("=")
            form_data[key] = value.replace("+", " ")

    question = form_data.get("text", "").strip()
    team_id = form_data.get("team_id", "")
    slack_user_id = form_data.get("user_id", "")

    if not question:
        return {"response_type": "ephemeral", "text": "Please provide a question. Example: `/ask What is our refund policy?`"}

    # Find tenant associated with this Slack team
    # WHY? Each Slack workspace (team_id) maps to one tenant.
    # In production, you'd store team_id when the user installs the Slack app.
    # For the demo, we use the first available tenant.
    tenant = db.query(TenantModel).first()
    if not tenant:
        return {"response_type": "ephemeral", "text": "No tenant found. Please set up your account at the AskMyDocs dashboard."}

    # Get a user to attribute this request to (use admin user for Slack)
    admin_user = db.query(UserModel).filter(
        UserModel.tenant_id == tenant.id,
        UserModel.role == "admin",
    ).first()
    if not admin_user:
        return {"response_type": "ephemeral", "text": "Configuration error: no admin user found"}

    # Find relevant document chunks
    chunks = rag.find_relevant_chunks(
        query=question,
        tenant_id=tenant.id,
        document_id=None,
        top_k=3,
        db=db,
    )

    if not chunks:
        return {
            "response_type": "in_channel",
            "text": f"*Question:* {question}\n\n*Answer:* I don't have any relevant documents to answer this. Please upload documents to AskMyDocs first.",
        }

    # Get answer from LLM
    prompt = rag.build_rag_prompt(question, chunks, tenant.name)
    try:
        response = ollama.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,  # Keep Slack responses concise
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        return {"response_type": "ephemeral", "text": f"AI service error: {e}"}

    # Log usage
    db.add(UsageLogModel(
        tenant_id=tenant.id,
        user_id=admin_user.id,
        endpoint="/slack/ask",
        model=AI_MODEL,
        input_tokens=len(prompt.split()),
        output_tokens=len(answer.split()),
    ))
    db.commit()

    # Format Slack response using Block Kit for rich formatting
    return {
        "response_type": "in_channel",  # "in_channel" = visible to everyone; "ephemeral" = only requester
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Question from <@{slack_user_id}>:*\n{question}"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Answer:*\n{answer}"},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"_Powered by AskMyDocs Pro | {tenant.name}_"},
                ],
            },
        ],
    }


# ─── Usage Stats ──────────────────────────────────────────────────────────────

@app.get("/usage", tags=["Tenant"])
def get_usage(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detailed usage statistics for the current tenant this month."""
    tenant_id = current_user["tenant_id"]
    tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    logs = db.query(UsageLogModel).filter(
        UsageLogModel.tenant_id == tenant_id,
        UsageLogModel.timestamp >= month_start,
    ).all()

    by_endpoint: dict[str, int] = {}
    by_day: dict[str, int] = {}
    total_cost = 0.0

    for log in logs:
        by_endpoint[log.endpoint] = by_endpoint.get(log.endpoint, 0) + 1
        day = log.timestamp.strftime("%Y-%m-%d")
        by_day[day] = by_day.get(day, 0) + 1
        total_cost += log.cost_usd or 0

    used = len(logs)
    quota = tenant.monthly_quota if tenant else 50
    remaining = None if quota == -1 else max(0, quota - used)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant.name if tenant else "unknown",
        "plan": tenant.plan if tenant else "free",
        "month": now.strftime("%B %Y"),
        "used": used,
        "quota": quota if quota != -1 else "unlimited",
        "remaining": remaining if remaining is not None else "unlimited",
        "total_cost_usd": round(total_cost, 6),
        "by_endpoint": by_endpoint,
        "by_day": by_day,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
