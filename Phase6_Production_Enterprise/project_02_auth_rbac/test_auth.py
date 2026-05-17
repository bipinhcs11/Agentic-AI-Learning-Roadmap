# ═══════════════════════════════════════════════════════════════
# Project 02 — Auth & RBAC · test_auth.py
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   End-to-end demo / smoke test for the auth system.
#   Runs against a live server at localhost:8000.
#   NOT a pytest suite — run it directly with Python.
#
# HOW TO RUN:
#   # 1. Start the server (in another terminal):
#   #    uvicorn main:app --reload
#   #
#   # 2. Run this script:
#   python test_auth.py
#
# WHAT IT TESTS:
#   1. Health endpoint (open)
#   2. Register a viewer user
#   3. Login and receive JWT
#   4. Authenticated chat request (viewer — should PASS)
#   5. Viewer tries /stats (admin-only) — should be REJECTED (403)
#   6. Register + login as developer — access /models
#   7. Developer tries /stats — should be REJECTED (403)
#   8. Login as admin — access /stats
#   9. Generate an API key via Bearer token
#  10. Use API key (X-API-Key header) instead of Bearer token
#  11. Invalid token — should be REJECTED (401)
# ═══════════════════════════════════════════════════════════════

import sys
import time

import requests

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

BASE_URL  = "http://localhost:8000"
SEPARATOR = "─" * 60


# ─────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────

pass_count = 0
fail_count = 0


def result(label: str, passed: bool, detail: str = "") -> None:
    """Print a single test result line and update counters."""
    global pass_count, fail_count
    icon = "PASS" if passed else "FAIL"
    msg  = f"  [{icon}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if passed:
        pass_count += 1
    else:
        fail_count += 1


def section(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def post(path: str, body: dict, token: str = "", api_key: str = "") -> requests.Response:
    headers = build_headers(token, api_key)
    return requests.post(f"{BASE_URL}{path}", json=body, headers=headers, timeout=10)


def get(path: str, token: str = "", api_key: str = "") -> requests.Response:
    headers = build_headers(token, api_key)
    return requests.get(f"{BASE_URL}{path}", headers=headers, timeout=10)


def build_headers(token: str, api_key: str) -> dict:
    h = {}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if api_key:
        h["X-API-Key"] = api_key
    return h


# ═══════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════

def test_health() -> None:
    section("Test 1 — Health Endpoint (open, no auth)")
    resp = get("/health")
    result("GET /health returns 200", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    result("Response has 'status' field", "status" in data, data.get("status", "?"))


def register_and_login(username: str, password: str, email: str, role: str) -> str:
    """Helper: register user (ignore 400 if already exists), then login and return token."""
    post("/auth/register", {
        "username": username,
        "email":    email,
        "password": password,
        "role":     role,
    })
    resp = post("/auth/login", {"username": username, "password": password})
    if resp.status_code != 200:
        print(f"  [WARN] Login failed for {username}: {resp.text}")
        return ""
    return resp.json().get("access_token", "")


def test_register_viewer() -> str:
    section("Test 2 — Register a Viewer user")
    # Use a unique username so re-runs don't clash (server keeps the DB)
    username = f"viewer_{int(time.time())}"
    resp = post("/auth/register", {
        "username": username,
        "email":    f"{username}@example.com",
        "password": "viewerpass",
        "role":     "viewer",
    })
    result("POST /auth/register returns 201", resp.status_code == 201, str(resp.status_code))
    data = resp.json()
    result("Returned role is 'viewer'", data.get("role") == "viewer", data.get("role"))
    return username


def test_login(username: str) -> str:
    section("Test 3 — Login and receive JWT")
    resp = post("/auth/login", {"username": username, "password": "viewerpass"})
    result("POST /auth/login returns 200", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    has_token = bool(data.get("access_token"))
    result("Response contains access_token", has_token, "yes" if has_token else "MISSING")
    result("Token type is 'bearer'", data.get("token_type") == "bearer", data.get("token_type"))
    return data.get("access_token", "")


def test_viewer_chat(token: str) -> None:
    section("Test 4 — Viewer can POST /chat")
    resp = post("/chat", {"message": "Say hello in one word"}, token=token)
    # We accept 200 (Ollama running) OR 503 (Ollama offline) — both mean auth passed
    auth_ok = resp.status_code not in (401, 403)
    result(
        "Viewer can reach /chat (not blocked by auth)",
        auth_ok,
        f"status={resp.status_code}",
    )


def test_viewer_blocked_from_stats(token: str) -> None:
    section("Test 5 — Viewer is BLOCKED from /stats (admin only)")
    resp = get("/stats", token=token)
    result(
        "GET /stats returns 403 for viewer",
        resp.status_code == 403,
        f"status={resp.status_code}",
    )


def test_developer_flow() -> None:
    section("Test 6 — Developer can access /models")
    username = f"dev_{int(time.time())}"
    token = register_and_login(username, "devpass", f"{username}@example.com", "developer")
    if not token:
        result("Developer login", False, "token empty")
        return

    resp = get("/models", token=token)
    auth_ok = resp.status_code not in (401, 403)
    result(
        "Developer can reach /models (not blocked by auth)",
        auth_ok,
        f"status={resp.status_code}",
    )

    # Developer should still be blocked from /stats
    resp2 = get("/stats", token=token)
    result(
        "GET /stats returns 403 for developer",
        resp2.status_code == 403,
        f"status={resp2.status_code}",
    )


def test_admin_flow() -> str:
    section("Test 7 — Admin can access /stats")
    # Default admin is seeded by init_db() on first startup
    resp = post("/auth/login", {"username": "admin", "password": "admin123"})
    result("Admin login returns 200", resp.status_code == 200, str(resp.status_code))
    token = resp.json().get("access_token", "")
    if not token:
        result("Admin token present", False, "empty")
        return ""

    resp2 = get("/stats", token=token)
    result("Admin GET /stats returns 200", resp2.status_code == 200, str(resp2.status_code))
    return token


def test_api_key_flow(bearer_token: str) -> None:
    section("Test 8 — Generate API key via Bearer, then use X-API-Key")

    # ── Generate key ─────────────────────────────────────────
    resp = post("/auth/api-key", {}, token=bearer_token)
    result("POST /auth/api-key returns 200", resp.status_code == 200, str(resp.status_code))
    api_key = resp.json().get("api_key", "")
    result("API key returned", bool(api_key), "yes" if api_key else "MISSING")

    if not api_key:
        return

    # ── Use the raw API key (no Bearer token) ────────────────
    resp2 = get("/auth/me", api_key=api_key)
    result(
        "GET /auth/me with X-API-Key returns 200",
        resp2.status_code == 200,
        str(resp2.status_code),
    )
    if resp2.status_code == 200:
        result(
            "X-API-Key identifies correct user",
            resp2.json().get("username") == "admin",
            resp2.json().get("username"),
        )

    # Admin using API key can still hit /stats
    resp3 = get("/stats", api_key=api_key)
    result(
        "Admin X-API-Key can access /stats",
        resp3.status_code == 200,
        str(resp3.status_code),
    )


def test_invalid_token() -> None:
    section("Test 9 — Invalid / tampered token is REJECTED")
    resp = get("/auth/me", token="this.is.not.a.valid.jwt")
    result(
        "Tampered token returns 401",
        resp.status_code == 401,
        f"status={resp.status_code}",
    )

    # No token at all
    resp2 = get("/auth/me")
    result(
        "Missing token returns 401",
        resp2.status_code == 401,
        f"status={resp2.status_code}",
    )


def test_duplicate_register() -> None:
    section("Test 10 — Duplicate registration returns 400")
    # Register the same user twice — second call must fail
    payload = {
        "username": "duplicate_user",
        "email":    "dup@example.com",
        "password": "pass123",
        "role":     "viewer",
    }
    post("/auth/register", payload)   # first — may succeed or already exist
    resp = post("/auth/register", payload)  # second — must 400
    result(
        "Duplicate username returns 400",
        resp.status_code == 400,
        str(resp.status_code),
    )


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    print("\n" + "═" * 60)
    print("  Phase 6 Project 02 — Auth & RBAC Test Suite")
    print("  Target:", BASE_URL)
    print("═" * 60)

    # Verify the server is reachable before running tests
    try:
        requests.get(f"{BASE_URL}/health", timeout=3)
    except Exception:
        print(f"\n  ERROR: Cannot reach {BASE_URL}")
        print("  Start the server first:  uvicorn main:app --reload")
        sys.exit(1)

    # ── Run all tests ─────────────────────────────────────────
    test_health()

    viewer_username = test_register_viewer()
    viewer_token    = test_login(viewer_username) if viewer_username else ""

    if viewer_token:
        test_viewer_chat(viewer_token)
        test_viewer_blocked_from_stats(viewer_token)

    test_developer_flow()
    admin_token = test_admin_flow()

    if admin_token:
        test_api_key_flow(admin_token)

    test_invalid_token()
    test_duplicate_register()

    # ── Summary ───────────────────────────────────────────────
    total = pass_count + fail_count
    print(f"\n{'═' * 60}")
    print(f"  Results: {pass_count}/{total} passed", end="")
    if fail_count:
        print(f"  |  {fail_count} FAILED ← investigate above")
    else:
        print("  — all green!")
    print("═" * 60 + "\n")

    # Exit non-zero so CI pipelines can detect failures
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
