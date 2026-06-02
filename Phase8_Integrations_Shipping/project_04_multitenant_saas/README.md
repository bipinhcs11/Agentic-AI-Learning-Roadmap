# Project 04: Multi-Tenant SaaS Platform

## What Multi-Tenancy Means

Multi-tenancy is the architecture where **a single instance of your software serves multiple customers (tenants)**, with each tenant's data completely isolated from others.

Think of it like an apartment building: one building (your app), many apartments (tenants), each with a locked door. The building manager (super-admin) has a master key. Tenants can only enter their own apartment.

### Why Multi-Tenancy?

| Approach | Cost | Isolation | Complexity |
|----------|------|-----------|------------|
| Single-tenant (one instance per customer) | Very high | Perfect | Low per-instance |
| Multi-tenant (shared instance) | Low | Good (by design) | Higher upfront |

Most SaaS companies (Slack, Notion, Linear, GitHub) use multi-tenancy because:
- One codebase to maintain, one deployment to operate
- Economies of scale (shared infrastructure)
- Easier to roll out updates (one deployment, not thousands)

## Data Isolation Strategies

### 1. Row-Level Isolation (This project)
Every table has a `tenant_id` column. Every query adds `WHERE tenant_id = ?`.

```sql
-- Every query looks like this:
SELECT * FROM users WHERE tenant_id = 42 AND email = ?
```

**Pros:** Simple, works with any database, easy to migrate tenants  
**Cons:** One bug in query = data leak (must be vigilant)  
**Used by:** Most SQL-based SaaS products

### 2. Schema-Level Isolation
Each tenant gets their own PostgreSQL schema (`acme_corp.users`, `startup_inc.users`).

```sql
-- Tenant A's query:
SET search_path TO acme_corp;
SELECT * FROM users WHERE email = ?

-- Tenant B's query:
SET search_path TO startup_inc;
SELECT * FROM users WHERE email = ?
```

**Pros:** Stronger isolation, easier per-tenant migrations  
**Cons:** Schema management complexity, PostgreSQL-specific  
**Used by:** Larger SaaS with stricter isolation requirements

### 3. Database-Level Isolation
Each tenant gets their own database server.

**Pros:** Maximum isolation, independent scaling  
**Cons:** Very expensive, complex ops  
**Used by:** Enterprise/regulated industries (healthcare, finance)

## Why We Chose Row-Level (This Project)

Row-level isolation is the right choice for:
- Getting started quickly
- SQLite (no schema-level support)
- Most SaaS products (the risk is manageable with proper code review)

The critical safeguard: **every database function must filter by tenant_id**. We enforce this by extracting tenant_id from the JWT in a FastAPI dependency, making it impossible to forget.

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000

# Run tests (in a separate terminal)
python test_multitenant.py
```

API docs at: http://localhost:8000/docs

## Demo Tenants (Created on Startup)

| Tenant | Plan | Quota | Admin Email | Password |
|--------|------|-------|-------------|----------|
| Acme Corp | pro | 1,000/month | admin@acme-corp.example | acme-admin-pass |
| Startup Inc | free | 100/month | admin@startup-inc.example | startup-admin-pass |
| BigCorp Enterprise | enterprise | unlimited | admin@bigcorp.example | bigcorp-admin-pass |

**Super-admin token:** `superadmin-dev-token-change-in-production`

## API Endpoints

### Auth Flow
```bash
# Login (gets tenant-scoped JWT)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@acme-corp.example", "password": "acme-admin-pass"}'

# Use the token
export TOKEN="<token from login response>"

# Check your tenant
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/tenants/me

# Chat (quota enforced)
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

### Super-Admin
```bash
# List all tenants
curl -H "Authorization: Bearer superadmin-dev-token-change-in-production" \
  http://localhost:8000/admin/tenants

# Create new tenant
curl -X POST http://localhost:8000/tenants \
  -H "Authorization: Bearer superadmin-dev-token-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Customer", "slug": "new-customer", "plan": "pro"}'
```

## How to Migrate to PostgreSQL with Row-Level Security

PostgreSQL has native Row-Level Security (RLS) — a database-enforced guarantee that no query can return rows from other tenants, even if the application has a bug.

### Step 1: Switch database URL

```python
# In main.py, change:
DATABASE_URL = "sqlite:///./multitenant.db"
# To:
DATABASE_URL = "postgresql://user:password@localhost/saasdb"
```

### Step 2: Enable RLS in PostgreSQL

```sql
-- Enable RLS on each table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Create policy: users can only see their own tenant's rows
CREATE POLICY tenant_isolation ON users
  USING (tenant_id = current_setting('app.tenant_id')::integer);

CREATE POLICY tenant_isolation ON usage_logs
  USING (tenant_id = current_setting('app.tenant_id')::integer);
```

### Step 3: Set tenant context per request

```python
# In your FastAPI dependency, after verifying the JWT:
db.execute(text(f"SET app.tenant_id = {tenant_id}"))
```

Now PostgreSQL enforces isolation at the database layer — even a SQL injection can't access other tenants' data.

## Key Learning Points

1. **JWT contains tenant_id** — avoids a DB lookup on every request
2. **FastAPI dependencies** — elegant way to enforce auth + quota on every endpoint
3. **Quota enforcement returns HTTP 429** — correct HTTP semantics for rate limiting
4. **Seed on startup** — makes the demo immediately runnable
5. **Super-admin uses a separate token** — not a tenant-scoped JWT (it crosses tenant boundaries)
