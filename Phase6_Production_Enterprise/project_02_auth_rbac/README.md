# Phase 6 · Project 02 — JWT Auth & RBAC

Production authentication and role-based access control layer added on top of the AI Platform API from Project 01.

---

## What this adds

| Feature | Detail |
|---|---|
| JWT tokens | `python-jose`, HS256, 24-hour expiry |
| Password hashing | `passlib[bcrypt]` |
| API key auth | uuid4-based, stored as SHA-256 hash |
| Database | SQLite via SQLAlchemy (auto-created as `auth.db`) |
| Dual auth headers | `Authorization: Bearer <token>` or `X-API-Key: <key>` |

---

## JWT Flow

```
Client                           Server
  |                                |
  |-- POST /auth/register -------> |  Create user (open)
  |<-- 201 { id, username, role } -|
  |                                |
  |-- POST /auth/login ----------> |  Verify password
  |<-- 200 { access_token, role } -|  JWT signed with SECRET_KEY
  |                                |
  |-- GET /models                  |
  |   Authorization: Bearer <jwt> >|  verify_token() → role check
  |<-- 200 { models: [...] } ------|
```

The JWT payload contains `sub` (username), `role`, and `user_id` so protected endpoints can authorise without an extra DB lookup.

---

## Role Permission Matrix

| Endpoint | viewer | developer | admin |
|---|:---:|:---:|:---:|
| `GET /health` | open | open | open |
| `POST /auth/register` | open | open | open |
| `POST /auth/login` | open | open | open |
| `POST /auth/api-key` | yes | yes | yes |
| `GET /auth/me` | yes | yes | yes |
| `POST /chat` | yes | yes | yes |
| `POST /chat/stream` | yes | yes | yes |
| `GET /models` | no | yes | yes |
| `GET /stats` | no | no | yes |

---

## Quick Start

### Local (no Docker)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
uvicorn main:app --reload --port 8000

# 3. Run the test suite (separate terminal)
python test_auth.py
```

On first startup the server auto-creates a default admin account:
- Username: `admin`
- Password: `admin123`

### Docker

```bash
# Build
docker build -t auth-api .

# Run (with persistent DB volume)
docker run -p 8000:8000 \
  -v $(pwd)/data:/data \
  -e DB_PATH=/data/auth.db \
  -e SECRET_KEY=your-secret-here \
  auth-api
```

---

## Example curl calls

### Register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"pass123","role":"developer"}'
```

### Login

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"pass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Chat (Bearer token)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```

### Generate API key

```bash
API_KEY=$(curl -s -X POST http://localhost:8000/auth/api-key \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])")
```

### Use API key instead of Bearer token

```bash
curl http://localhost:8000/auth/me \
  -H "X-API-Key: $API_KEY"
```

---

## Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-in-production` | **Change this in production** |
| `DB_PATH` | `./auth.db` | SQLite file path |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama endpoint |
| `DEFAULT_MODEL` | `gemma3:4b` | Fallback model |
| `RATE_LIMIT_RPM` | `30` | Requests per minute per user |
| `APP_ENV` | `development` | Set to `production` in Docker |

---

## API Docs

Interactive Swagger UI: <http://localhost:8000/docs>
