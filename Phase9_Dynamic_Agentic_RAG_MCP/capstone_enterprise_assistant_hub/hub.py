"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Capstone | hub.py                                                ║
║  CLI and thin FastAPI entrypoint for the Enterprise Assistant Hub.           ║
║                                                                              ║
║  RUN: python hub.py --tenant acme "What is the 2026 employee primary contribution limit?"   ║
║  API: uvicorn hub:app --reload                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import os
from typing import Optional

from pydantic import BaseModel

try:
    from .config import tenant_for_api_key
    from .orchestrator import answer_question
except ImportError:  # pragma: no cover
    from config import tenant_for_api_key
    from orchestrator import answer_question


class ChatRequest(BaseModel):
    question: str


def _result_payload(result) -> dict:
    return {
        "answer": result.answer,
        "route": result.route,
        "tools_used": result.tools_used,
        "documents_used": result.documents_used,
        "provider": result.provider,
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "sources": result.sources,
    }


def create_app():
    from fastapi import FastAPI, Header, HTTPException

    app = FastAPI(
        title="Phase 9 Enterprise Assistant Hub",
        description="Mock multi-tenant MCP + RAG assistant. Educational only.",
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "provider": os.getenv("AI_PROVIDER", "ollama")}

    @app.post("/chat")
    def chat(body: ChatRequest, x_api_key: Optional[str] = Header(default=None)) -> dict:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key")
        try:
            tenant = tenant_for_api_key(x_api_key)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Unknown API key")
        return _result_payload(answer_question(body.question, tenant.tenant_id))

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the Phase 9 Enterprise Assistant Hub.")
    parser.add_argument("question", nargs="+", help="Question to ask")
    parser.add_argument("--tenant", default="acme", help="Tenant id from config/tenants.yaml")
    parser.add_argument(
        "--rag-only",
        action="store_true",
        help="Set ENABLE_MCP=false for a direct tenant RAG answer.",
    )
    args = parser.parse_args()
    if args.rag_only:
        os.environ["ENABLE_MCP"] = "false"

    question = " ".join(args.question)
    result = answer_question(question, args.tenant)
    print("\nANSWER:\n" + result.answer.strip())
    print("\nMETA:")
    print(json.dumps(_result_payload(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
