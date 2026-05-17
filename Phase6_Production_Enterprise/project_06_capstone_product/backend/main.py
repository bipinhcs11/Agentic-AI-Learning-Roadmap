"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           DocuMind — FastAPI Backend                                         ║
║           Phase 6 / Project 06 Capstone — Agentic AI Learning Roadmap       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Architecture:                                                               ║
║    • JWT auth (python-jose) — inline, no external auth service               ║
║    • SQLite via SQLAlchemy for users / documents / query_logs                ║
║    • In-memory VectorStore (numpy cosine similarity) for embeddings          ║
║    • LangGraph RAG pipeline (rag_pipeline.py) handles multi-agent Q&A        ║
║    • Document files persisted to ./documents/ mount                          ║
║                                                                              ║
║  Startup behaviour:                                                          ║
║    • Creates DB tables on first run                                          ║
║    • Seeds admin/admin123 user if no users exist                             ║
║    • Re-indexes any documents already on disk (crash recovery)               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
import uuid
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import (
    Depends, FastAPI, File, HTTPException, Request, UploadFile, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import (
    Column, DateTime, Integer, String, Text, create_engine, func
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from document_processor import DocumentProcessor
from rag_pipeline import RAGPipeline, vector_store

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

SECRET_KEY: str = os.getenv("SECRET_KEY", "documind-dev-secret-change-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS: int = 24

DB_PATH: str = os.getenv("DB_PATH", "/app/db/documind.db")
DOCUMENTS_DIR: str = os.getenv("DOCUMENTS_DIR", "/app/documents")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE_MB = 20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("documind")


# ─────────────────────────────────────────────────────────────────────────────
# Database — SQLAlchemy models
# ─────────────────────────────────────────────────────────────────────────────

# Ensure directories exist before creating engine
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
Path(DOCUMENTS_DIR).mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")   # "admin" | "user"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    size_bytes = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class QueryLogModel(Base):
    __tablename__ = "query_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    answer_length = Column(Integer, default=0)
    quality_score = Column(Integer, default=0)
    # Approximate token usage (prompt + completion) for cost dashboard
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    payload = decode_token(token)
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas (request / response bodies)
# ─────────────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class DocumentOut(BaseModel):
    id: str
    filename: str
    size_bytes: int
    chunk_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    question: str


class CitationOut(BaseModel):
    filename: str
    excerpt: str
    score: str


class QueryResponse(BaseModel):
    answer: str
    citations: List[CitationOut]
    quality_score: int
    quality_note: str


class AdminStatsResponse(BaseModel):
    total_users: int
    total_documents: int
    total_queries: int
    total_tokens_used: int
    avg_quality_score: float


# ─────────────────────────────────────────────────────────────────────────────
# Application startup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="DocuMind API",
    description="Internal Document Intelligence Platform — Phase 6 Capstone",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = DocumentProcessor()
rag = RAGPipeline()


def _seed_admin(db: Session) -> None:
    """Create default admin account on first run."""
    if db.query(UserModel).count() == 0:
        admin = UserModel(
            id=str(uuid.uuid4()),
            username="admin",
            hashed_password=hash_password("admin123"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        logger.info("Seeded default admin user (admin/admin123)")


def _reindex_documents(db: Session) -> None:
    """
    On restart, re-embed documents that are on disk but not yet in the
    in-memory VectorStore.  This handles container restarts gracefully
    without requiring a persistent vector database.
    """
    docs = db.query(DocumentModel).all()
    reindexed = 0
    for doc in docs:
        if vector_store.has_document(doc.id):
            continue
        file_path = Path(doc.file_path)
        if not file_path.exists():
            logger.warning("File missing on disk for doc_id=%s (%s)", doc.id, doc.filename)
            continue
        try:
            data = file_path.read_bytes()
            chunks = processor.process(doc.id, doc.filename, data)
            vector_store.add_document(doc.id, chunks, doc.filename)
            reindexed += 1
        except Exception as exc:
            logger.error("Failed to reindex %s: %s", doc.filename, exc)

    if reindexed:
        logger.info("Reindexed %d documents after restart", reindexed)


@app.on_event("startup")
def startup_event() -> None:
    db = SessionLocal()
    try:
        _seed_admin(db)
        _reindex_documents(db)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Auth endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Standard OAuth2 password flow. Returns a 24-hour JWT."""
    user = db.query(UserModel).filter(UserModel.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": user.id, "role": user.role})
    return TokenResponse(access_token=token, role=user.role)


@app.post("/auth/register", response_model=TokenResponse, tags=["auth"])
async def register(
    req: UserCreateRequest,
    db: Session = Depends(get_db),
):
    """Self-registration for new users (role defaults to 'user')."""
    if db.query(UserModel).filter(UserModel.username == req.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")

    # Only admins may create admin accounts via /admin/users; self-reg is always 'user'
    user = UserModel(
        id=str(uuid.uuid4()),
        username=req.username,
        hashed_password=hash_password(req.password),
        role="user",
    )
    db.add(user)
    db.commit()
    token = create_access_token({"sub": user.id, "role": user.role})
    return TokenResponse(access_token=token, role=user.role)


# ─────────────────────────────────────────────────────────────────────────────
# Document endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/documents/upload", response_model=DocumentOut, tags=["documents"])
async def upload_document(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accepts PDF, TXT, or MD files up to MAX_FILE_SIZE_MB.
    Processing pipeline: read → validate → save → chunk → embed → index.
    """
    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    data = await file.read()

    if len(data) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit",
        )

    # Persist to disk
    doc_id = str(uuid.uuid4())
    safe_name = f"{doc_id}{suffix}"
    file_path = Path(DOCUMENTS_DIR) / safe_name
    file_path.write_bytes(data)

    # Chunk + embed
    try:
        chunks = processor.process(doc_id, file.filename, data)
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        logger.error("Processing failed for %s: %s", file.filename, exc)
        raise HTTPException(status_code=500, detail="Document processing failed") from exc

    # Index into VectorStore
    vector_store.add_document(doc_id, chunks, file.filename)

    # Persist metadata
    doc = DocumentModel(
        id=doc_id,
        owner_id=current_user.id,
        filename=file.filename,
        file_path=str(file_path),
        size_bytes=len(data),
        chunk_count=len(chunks),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    logger.info(
        "User '%s' uploaded '%s' (%d bytes, %d chunks)",
        current_user.username, file.filename, len(data), len(chunks),
    )
    return doc


@app.get("/documents", response_model=List[DocumentOut], tags=["documents"])
async def list_documents(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns documents owned by the current user."""
    docs = (
        db.query(DocumentModel)
        .filter(DocumentModel.owner_id == current_user.id)
        .order_by(DocumentModel.uploaded_at.desc())
        .all()
    )
    return docs


@app.delete("/documents/{doc_id}", tags=["documents"])
async def delete_document(
    doc_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a document from disk, VectorStore, and database."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Admins may delete any document; regular users only their own
    if current_user.role != "admin" and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised to delete this document")

    # Remove from VectorStore first (in-memory)
    vector_store.remove_document(doc_id)

    # Remove from disk
    file_path = Path(doc.file_path)
    file_path.unlink(missing_ok=True)

    db.delete(doc)
    db.commit()

    logger.info("Deleted document '%s' (id=%s)", doc.filename, doc_id)
    return {"detail": "Document deleted successfully", "id": doc_id}


# ─────────────────────────────────────────────────────────────────────────────
# Query endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse, tags=["query"])
async def query_documents(
    req: QueryRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    RAG-powered Q&A.  The query is answered using only the current user's
    documents, ensuring data isolation between tenants.
    """
    # Collect this user's doc IDs
    user_doc_ids = [
        row.id
        for row in db.query(DocumentModel.id)
        .filter(DocumentModel.owner_id == current_user.id)
        .all()
    ]

    if not user_doc_ids:
        return QueryResponse(
            answer="You have no documents uploaded. Please upload documents before asking questions.",
            citations=[],
            quality_score=0,
            quality_note="No documents available",
        )

    # Run multi-agent pipeline
    start = time.monotonic()
    result = rag.run(query=req.question, doc_ids=user_doc_ids)
    elapsed = time.monotonic() - start

    # Approximate token usage: ~1 token per 4 chars is a reasonable heuristic
    approx_tokens = (len(req.question) + len(result["answer"])) // 4

    # Persist query for analytics
    log = QueryLogModel(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        query_text=req.question[:500],
        answer_length=len(result["answer"]),
        quality_score=result["quality_score"],
        tokens_used=approx_tokens,
    )
    db.add(log)
    db.commit()

    logger.info(
        "Query answered for user '%s' in %.2fs (quality=%d)",
        current_user.username, elapsed, result["quality_score"],
    )

    return QueryResponse(
        answer=result["answer"],
        citations=[CitationOut(**c) for c in result["citations"]],
        quality_score=result["quality_score"],
        quality_note=result["quality_note"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Admin endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/admin/stats", response_model=AdminStatsResponse, tags=["admin"])
async def admin_stats(
    _: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Aggregated usage metrics for the admin dashboard."""
    total_users = db.query(func.count(UserModel.id)).scalar() or 0
    total_docs = db.query(func.count(DocumentModel.id)).scalar() or 0
    total_queries = db.query(func.count(QueryLogModel.id)).scalar() or 0
    total_tokens = db.query(func.sum(QueryLogModel.tokens_used)).scalar() or 0
    avg_quality = db.query(func.avg(QueryLogModel.quality_score)).scalar() or 0.0

    return AdminStatsResponse(
        total_users=total_users,
        total_documents=total_docs,
        total_queries=total_queries,
        total_tokens_used=int(total_tokens),
        avg_quality_score=round(float(avg_quality), 2),
    )


@app.post("/admin/users", tags=["admin"])
async def create_user(
    req: UserCreateRequest,
    _: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: create a user with any role."""
    if db.query(UserModel).filter(UserModel.username == req.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")

    user = UserModel(
        id=str(uuid.uuid4()),
        username=req.username,
        hashed_password=hash_password(req.password),
        role=req.role,
    )
    db.add(user)
    db.commit()
    return {"id": user.id, "username": user.username, "role": user.role}


@app.get("/admin/users", tags=["admin"])
async def list_users(
    _: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(UserModel).all()
    return [
        {"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at}
        for u in users
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health():
    """Simple liveness probe for Docker / load balancer health checks."""
    return {
        "status": "ok",
        "service": "DocuMind API",
        "version": "1.0.0",
        "vector_store_docs": vector_store.document_count(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Entry point (for direct `python main.py` runs during development)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
