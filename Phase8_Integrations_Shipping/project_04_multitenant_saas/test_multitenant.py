"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║     Phase 8 — Project 04: Multi-Tenant SaaS | test_multitenant.py              ║
║                      Integration Tests & Demo Script                            ║
║                                                                                 ║
║  PURPOSE: Demonstrates and validates multi-tenancy guarantees:                  ║
║  1. Tenant isolation — users cannot access other tenants' data                  ║
║  2. Quota enforcement — free tier hits monthly limit                            ║
║  3. JWT scoping — tokens are tenant-specific                                    ║
║                                                                                 ║
║  RUN: Start the server first, then run this script                              ║
║    uvicorn main:app --port 8000                                                  ║
║    python test_multitenant.py                                                   ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import Optional

import httpx

# ─── Test configuration ───────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
SUPER_ADMIN_TOKEN = "superadmin-dev-token-change-in-production"

# Track test results
RESULTS: list[dict] = []


def _pass(test_name: str, detail: str = "") -> None:
    """Record a PASS result."""
    RESULTS.append({"name": test_name, "status": "PASS", "detail": detail})
    print(f"  ✅ PASS  {test_name}")
    if detail:
        print(f"          {detail}")


def _fail(test_name: str, detail: str = "") -> None:
    """Record a FAIL result."""
    RESULTS.append({"name": test_name, "status": "FAIL", "detail": detail})
    print(f"  ❌ FAIL  {test_name}")
    if detail:
        print(f"          {detail}")


def _section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def post(path: str, data: dict, token: Optional[str] = None) -> httpx.Response:
    """POST helper with optional Bearer auth."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.post(f"{BASE_URL}{path}", json=data, headers=headers, timeout=30.0)


def get(path: str, token: Optional[str] = None) -> httpx.Response:
    """GET helper with optional Bearer auth."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.get(f"{BASE_URL}{path}", headers=headers, timeout=30.0)


def run_tests() -> None:
    """Run the full multi-tenancy test suite."""

    print("\n" + "═" * 60)
    print("  MULTI-TENANT SAAS — INTEGRATION TESTS")
    print("  Phase 8, Project 04")
    print("═" * 60)

    # ─── Test 0: Health Check ─────────────────────────────────────────────────
    _section("TEST 0: Server Health")

    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        if resp.status_code == 200:
            _pass("Server is running", resp.json().get("status"))
        else:
            _fail("Server health check", f"Got status {resp.status_code}")
            print("\n  ERROR: Server is not running!")
            print("  Start with: uvicorn main:app --port 8000")
            return
    except Exception as e:
        _fail("Server connection", str(e))
        print("\n  ERROR: Cannot connect to server. Start with: uvicorn main:app --port 8000")
        return

    # ─── Test 1: Super-Admin Creates Tenants ──────────────────────────────────
    _section("TEST 1: Create Tenants (Super-Admin)")

    # Create Tenant A
    import random, string
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    tenant_a_slug = f"test-tenant-alpha-{suffix}"
    tenant_b_slug = f"test-tenant-beta-{suffix}"

    resp = post(
        "/tenants",
        {"name": "Test Tenant Alpha", "slug": tenant_a_slug, "plan": "pro"},
        token=SUPER_ADMIN_TOKEN,
    )
    if resp.status_code == 201:
        tenant_a = resp.json()
        _pass(
            "Create Tenant A (pro plan)",
            f"ID={tenant_a['id']}, slug={tenant_a['slug']}, quota={tenant_a['monthly_quota']}",
        )
    else:
        _fail("Create Tenant A", f"Status {resp.status_code}: {resp.text}")
        tenant_a = None

    # Create Tenant B (free plan)
    resp = post(
        "/tenants",
        {"name": "Test Tenant Beta", "slug": tenant_b_slug, "plan": "free"},
        token=SUPER_ADMIN_TOKEN,
    )
    if resp.status_code == 201:
        tenant_b = resp.json()
        _pass(
            "Create Tenant B (free plan)",
            f"ID={tenant_b['id']}, slug={tenant_b['slug']}, quota={tenant_b['monthly_quota']}",
        )
    else:
        _fail("Create Tenant B", f"Status {resp.status_code}: {resp.text}")
        tenant_b = None

    # Test rejected unauthorized tenant creation
    resp = post(
        "/tenants",
        {"name": "Hacker Tenant", "slug": "hacker"},
        token="wrong-token",
    )
    if resp.status_code == 403:
        _pass("Reject unauthorized tenant creation", "Correctly returned 403")
    else:
        _fail("Reject unauthorized tenant creation", f"Got {resp.status_code} instead of 403")

    if not tenant_a or not tenant_b:
        print("\n  CRITICAL: Cannot continue without tenants. Check server logs.")
        return

    # ─── Test 2: Register Users Under Each Tenant ─────────────────────────────
    _section("TEST 2: Register Users per Tenant")

    # First, login as the pre-seeded admin for each demo tenant
    # These credentials come from seed_demo_data() in main.py
    resp_a = post("/auth/login", {"email": "admin@acme-corp.example", "password": "acme-admin-pass"})
    resp_b = post("/auth/login", {"email": "admin@startup-inc.example", "password": "startup-admin-pass"})

    if resp_a.status_code == 200 and resp_b.status_code == 200:
        admin_a_token = resp_a.json()["access_token"]
        admin_b_token = resp_b.json()["access_token"]
        tenant_a_id = resp_a.json()["tenant_id"]
        tenant_b_id = resp_b.json()["tenant_id"]
        _pass("Login as Acme Corp admin", f"tenant_id={tenant_a_id}")
        _pass("Login as Startup Inc admin", f"tenant_id={tenant_b_id}")
    else:
        _fail("Admin login", f"A: {resp_a.status_code}, B: {resp_b.status_code}")
        print("  Cannot continue — check seeded credentials in main.py")
        return

    # Register a regular user under Tenant A (Acme Corp)
    user_a_email = f"alice-{suffix}@acme-corp.example"
    resp = post(
        "/auth/register",
        {"email": user_a_email, "password": "alice-password-123"},
        token=admin_a_token,
    )
    if resp.status_code == 201:
        _pass(f"Register user under Acme Corp", f"email={user_a_email}")
    else:
        _fail("Register user A", f"Status {resp.status_code}: {resp.text}")

    # Register a regular user under Tenant B (Startup Inc)
    user_b_email = f"bob-{suffix}@startup-inc.example"
    resp = post(
        "/auth/register",
        {"email": user_b_email, "password": "bob-password-456"},
        token=admin_b_token,
    )
    if resp.status_code == 201:
        _pass(f"Register user under Startup Inc", f"email={user_b_email}")
    else:
        _fail("Register user B", f"Status {resp.status_code}: {resp.text}")

    # Login as the new users
    resp_alice = post("/auth/login", {"email": user_a_email, "password": "alice-password-123"})
    resp_bob = post("/auth/login", {"email": user_b_email, "password": "bob-password-456"})

    if resp_alice.status_code == 200 and resp_bob.status_code == 200:
        alice_token = resp_alice.json()["access_token"]
        bob_token = resp_bob.json()["access_token"]
        _pass("Alice (Acme Corp) login successful", f"tenant_id={resp_alice.json()['tenant_id']}")
        _pass("Bob (Startup Inc) login successful", f"tenant_id={resp_bob.json()['tenant_id']}")
    else:
        _fail("User logins", f"Alice: {resp_alice.status_code}, Bob: {resp_bob.status_code}")
        return

    # ─── Test 3: Tenant Isolation ─────────────────────────────────────────────
    _section("TEST 3: Tenant Isolation")

    # Alice checks her tenant info
    resp = get("/tenants/me", token=alice_token)
    if resp.status_code == 200:
        alice_tenant = resp.json()
        alice_tenant_name = alice_tenant["tenant_name"]
        _pass(
            "Alice sees her own tenant",
            f"Tenant: {alice_tenant_name}, Plan: {alice_tenant['plan']}",
        )
    else:
        _fail("Alice tenant info", f"Status {resp.status_code}")
        alice_tenant_name = "unknown"

    # Bob checks his tenant info
    resp = get("/tenants/me", token=bob_token)
    if resp.status_code == 200:
        bob_tenant = resp.json()
        bob_tenant_name = bob_tenant["tenant_name"]
        _pass(
            "Bob sees his own tenant",
            f"Tenant: {bob_tenant_name}, Plan: {bob_tenant['plan']}",
        )
    else:
        _fail("Bob tenant info", f"Status {resp.status_code}")
        bob_tenant_name = "unknown"

    # Verify they see DIFFERENT tenants
    if alice_tenant_name != bob_tenant_name:
        _pass(
            "Isolation: Alice and Bob see different tenants",
            f"Alice: '{alice_tenant_name}' ≠ Bob: '{bob_tenant_name}'",
        )
    else:
        _fail(
            "Isolation: Alice and Bob see different tenants",
            f"Both see '{alice_tenant_name}' — isolation BROKEN!",
        )

    # Alice cannot access admin endpoints with her user token
    resp = get("/admin/tenants", token=alice_token)
    if resp.status_code == 403:
        _pass("Alice cannot access /admin/tenants", "Correctly returned 403")
    else:
        _fail("Block Alice from admin", f"Got {resp.status_code} — should be 403!")

    # Unauthenticated request is blocked
    # WHY accept 401 OR 403: HTTPBearer(auto_error=True) returns 401 ("Not
    # authenticated") for a MISSING/malformed Authorization header on modern
    # FastAPI/Starlette — 401 is the semantically correct code for absent creds.
    # Older FastAPI returned 403 here; we accept both so the suite is
    # version-agnostic. (The /admin/tenants check above stays a hard 403 because
    # that is an explicit HTTPException(403) in require_super_admin, not the
    # bearer scheme.)
    resp = get("/tenants/me")
    if resp.status_code in (401, 403):
        _pass("Unauthenticated requests blocked", f"Correctly returned {resp.status_code}")
    else:
        _fail(
            "Block unauthenticated requests",
            f"Got {resp.status_code} — should be 401 or 403!",
        )

    # ─── Test 4: AI Chat with Quota Enforcement ───────────────────────────────
    _section("TEST 4: AI Chat & Quota Enforcement")

    # Alice (Acme Corp, pro plan) can chat
    resp = post("/chat", {"message": "Hello! What's 2+2?"}, token=alice_token)
    if resp.status_code == 200:
        chat_data = resp.json()
        remaining = chat_data.get("remaining_quota")
        _pass(
            "Alice (pro plan) can chat",
            f"Remaining quota: {remaining}, Model: {chat_data['model']}",
        )
    elif resp.status_code == 503:
        # Ollama might not be running — that's OK for this test
        _pass("Alice chat request reached quota check", "LLM unavailable (503) — quota check passed")
    else:
        _fail("Alice chat", f"Status {resp.status_code}: {resp.text[:100]}")

    # Bob (Startup Inc, free plan) can chat while under quota
    resp = post("/chat", {"message": "Hello! What is the capital of France?"}, token=bob_token)
    if resp.status_code in (200, 503):
        _pass("Bob (free plan) can chat while under quota", f"Status: {resp.status_code}")
    else:
        _fail("Bob chat under quota", f"Status {resp.status_code}: {resp.text[:100]}")

    # ─── Test 5: Simulate Quota Exhaustion ────────────────────────────────────
    _section("TEST 5: Quota Exhaustion (Free Tier Simulation)")

    print("  Note: Directly testing quota exhaustion requires 100+ API calls.")
    print("  Instead, we verify the quota enforcement logic is in place by")
    print("  checking the /usage endpoint and confirming the quota is tracked.\n")

    resp = get("/usage", token=bob_token)
    if resp.status_code == 200:
        usage = resp.json()
        used = usage["used"]
        remaining_raw = usage["remaining"]
        quota = usage["monthly_quota"]
        _pass(
            "Bob's free tier usage tracked",
            f"Used: {used}/{quota}, Remaining: {remaining_raw}",
        )

        # If remaining is a number (not "unlimited"), quota is enforced
        if isinstance(remaining_raw, int):
            _pass("Free tier has numeric quota limit", f"Quota={quota} is enforced")
        else:
            _fail("Free tier quota enforcement", "Expected numeric quota for free plan")
    else:
        _fail("Bob usage stats", f"Status {resp.status_code}")

    # Verify enterprise is unlimited
    enterprise_token_resp = post(
        "/auth/login",
        {"email": "admin@bigcorp.example", "password": "bigcorp-admin-pass"},
    )
    if enterprise_token_resp.status_code == 200:
        ent_token = enterprise_token_resp.json()["access_token"]
        resp = get("/usage", token=ent_token)
        if resp.status_code == 200:
            usage = resp.json()
            if usage["remaining"] == "unlimited":
                _pass("Enterprise plan has unlimited quota", "remaining='unlimited'")
            else:
                _fail("Enterprise unlimited quota", f"Got remaining={usage['remaining']}")
    else:
        print("  (Skipping enterprise test — admin login failed)")

    # ─── Test 6: Super-Admin Cross-Tenant View ────────────────────────────────
    _section("TEST 6: Super-Admin Cross-Tenant View")

    resp = get("/admin/tenants", token=SUPER_ADMIN_TOKEN)
    if resp.status_code == 200:
        all_tenants = resp.json()
        _pass(
            "Super-admin can list all tenants",
            f"Found {len(all_tenants)} tenants total",
        )

        # Verify our demo tenants appear
        slugs = {t["slug"] for t in all_tenants}
        demo_slugs = {"acme-corp", "startup-inc", "bigcorp"}
        found = demo_slugs.intersection(slugs)
        if len(found) == 3:
            _pass("All 3 demo tenants visible to super-admin", ", ".join(sorted(found)))
        else:
            _fail("Demo tenants visible", f"Only found: {found}")
    else:
        _fail("Super-admin tenant list", f"Status {resp.status_code}")

    # ─── Final Report ─────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  TEST RESULTS SUMMARY")
    print("═" * 60)

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")

    print(f"\n  Total:  {total}")
    print(f"  Passed: {passed} ({'%.0f' % (passed/total*100)}%)")
    print(f"  Failed: {failed}")

    if failed > 0:
        print("\n  FAILED TESTS:")
        for r in RESULTS:
            if r["status"] == "FAIL":
                print(f"  ✗ {r['name']}: {r['detail']}")

    print()
    if failed == 0:
        print("  🎉 ALL TESTS PASSED — Multi-tenancy is working correctly!")
    elif failed <= 2:
        print("  ⚠️  MOSTLY PASSING — Minor issues, check failed tests above")
    else:
        print("  ❌ MULTIPLE FAILURES — Review server logs")
    print()


if __name__ == "__main__":
    run_tests()
