"""
Local recording API for the Phase 9 Agent Playground.

Run:
    python demo_api.py

Then open:
    http://localhost:8090/

The endpoint shape matches the Spring Boot Module 05 playground API:
    POST /api/benefits/agent/ask
"""
from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from demo_agent_core import answer

HERE = Path(__file__).resolve().parent
PHASE9_DIR = HERE.parent
STATIC_DIR = (
    PHASE9_DIR
    / "module_05_springboot_mcp_benefits_assistant"
    / "src"
    / "main"
    / "resources"
    / "static"
)
DEFAULT_PORT = int(os.getenv("PYTHON_DEMO_PORT", "8090"))


class DemoApiHandler(BaseHTTPRequestHandler):
    server_version = "Phase9PythonDemo/1.0"

    def do_OPTIONS(self) -> None:
        self._send_headers(204, "text/plain", 0)

    def do_HEAD(self) -> None:
        if self.path == "/api/benefits/health":
            self._send_headers(200, "application/json", 0)
            return

        path = self.path.split("?", 1)[0]
        if path in ("", "/"):
            path = "/index.html"

        try:
            file_path = self._static_path(path)
        except ValueError:
            self.send_error(404, "Not found")
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "Not found")
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self._send_headers(200, content_type, file_path.stat().st_size)

    def do_GET(self) -> None:
        if self.path == "/api/benefits/health":
            self._send_json({"status": "ok", "backend": "python"})
            return

        path = self.path.split("?", 1)[0]
        if path in ("", "/"):
            path = "/index.html"

        try:
            file_path = self._static_path(path)
        except ValueError:
            self.send_error(404, "Not found")
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "Not found")
            return

        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self._send_headers(200, content_type, len(body))
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/benefits/agent/ask":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(400, "Request body must be JSON")
            return

        question = payload.get("question") if isinstance(payload, dict) else None
        self._send_json(answer(question))

    def log_message(self, format: str, *args: object) -> None:
        print("%s - - %s" % (self.address_string(), format % args))

    def _static_path(self, request_path: str) -> Path:
        relative = unquote(request_path).lstrip("/")
        candidate = (STATIC_DIR / relative).resolve()
        static_root = STATIC_DIR.resolve()
        if not str(candidate).startswith(str(static_root)):
            raise ValueError("Path escapes static root")
        return candidate

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send_headers(200, "application/json", len(body))
        self.wfile.write(body)

    def _send_headers(self, status: int, content_type: str, content_length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main() -> None:
    if not STATIC_DIR.exists():
        raise SystemExit(f"Static UI directory not found: {STATIC_DIR}")

    server = ThreadingHTTPServer(("localhost", DEFAULT_PORT), DemoApiHandler)
    print(f"Python Module 02 demo API running at http://localhost:{DEFAULT_PORT}/")
    print("POST /api/benefits/agent/ask returns the shared playground response shape.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Python Module 02 demo API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
