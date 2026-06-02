# AskMyDocs Pro — Pre-Launch Checklist

Complete every item before launching to real users. Each section is ordered by priority (most critical first).

---

## Security Checklist

### Critical (Must do before any public traffic)

- [ ] **Change all default secrets** — Replace every default value in your environment:
  - `SECRET_KEY` (JWT signing): `openssl rand -hex 32`
  - `SUPER_ADMIN_TOKEN`: `openssl rand -hex 32`
  - `SLACK_SIGNING_SECRET`: Get from Slack app dashboard
  - Database password (if using PostgreSQL)

- [ ] **Enable HTTPS** — No exceptions. Users must never send passwords over plain HTTP.
  - Use Certbot + Let's Encrypt: `certbot --nginx -d yourdomain.com`
  - Or use a managed TLS service (Cloudflare, AWS ALB)
  - Redirect all HTTP to HTTPS (301 redirect in nginx.conf)

- [ ] **Rotate JWT expiry** — Change `ACCESS_TOKEN_EXPIRE_MINUTES` to a reasonable value:
  - Web app: 24 hours (with refresh tokens)
  - API clients: 30 days (rotate manually)
  - Never: infinity

- [ ] **Review CORS settings** — In `backend/main.py`, change:
  ```python
  allow_origins=["https://yourdomain.com"]  # NOT "*"
  ```

- [ ] **Remove debug information from errors** — Never expose stack traces to end users.
  Set `app = FastAPI(debug=False)` in production.

- [ ] **Validate file uploads** — Check file content (magic bytes), not just extension.
  `file.content_type` can be spoofed. Use python-magic or validate PDF header.

- [ ] **Add rate limiting** — Prevent brute-force and DDoS:
  ```python
  # Add to FastAPI app
  pip install slowapi
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  ```

### Important (Do in first week)

- [ ] **Enable audit logging** — Log every login attempt, document access, and admin action.
  Send to a centralized log service (Papertrail, Datadog, CloudWatch).

- [ ] **Set up database backups** — For SQLite: nightly backup to S3.
  For PostgreSQL: pg_dump + WAL archiving.
  Test restore procedure before launch.

- [ ] **Implement session invalidation** — Currently, JWTs can't be revoked.
  Add a `token_blacklist` table or use short-lived tokens with refresh tokens.

- [ ] **Add CSRF protection** — FastAPI apps using cookies need CSRF tokens.
  If using JWT in Authorization header (current approach), CSRF isn't needed.

- [ ] **Security headers** — Add these to nginx.conf:
  ```nginx
  add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'";
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
  add_header Referrer-Policy "strict-origin-when-cross-origin";
  ```

---

## Performance Checklist

### Database

- [ ] **Add database indexes** — Run EXPLAIN QUERY PLAN on your most common queries.
  Add indexes on columns used in WHERE and JOIN clauses:
  ```sql
  CREATE INDEX idx_usage_logs_tenant_month ON usage_logs(tenant_id, timestamp);
  CREATE INDEX idx_chunks_tenant ON document_chunks(tenant_id);
  ```

- [ ] **Switch to PostgreSQL** — SQLite is not suitable for concurrent production traffic.
  ```bash
  pip install psycopg2-binary
  DATABASE_URL=postgresql://user:password@localhost/askmydocs
  ```
  Enable connection pooling with `pool_size=10, max_overflow=20`.

- [ ] **Migrate vector storage** — NumPy in-process vector search doesn't scale.
  For >1000 documents: use pgvector, Qdrant, or Pinecone.
  ```bash
  docker run -p 6333:6333 qdrant/qdrant
  pip install qdrant-client
  ```

### API

- [ ] **Add response caching** — Cache frequent identical queries:
  ```python
  pip install fastapi-cache2
  @cache(expire=300)  # Cache for 5 minutes
  async def get_tenant_stats(...):
  ```

- [ ] **Move document processing to background tasks** — Currently synchronous.
  Use Celery or FastAPI BackgroundTasks for large file indexing:
  ```python
  from fastapi import BackgroundTasks
  @app.post("/documents")
  async def upload(background_tasks: BackgroundTasks, ...):
      background_tasks.add_task(process_document, doc_id, file_bytes)
      return {"status": "processing", "document_id": doc_id}
  ```

- [ ] **Enable gzip compression** — Add to nginx.conf:
  ```nginx
  gzip on;
  gzip_types text/plain application/json;
  gzip_min_length 1000;
  ```

- [ ] **Configure Uvicorn workers** — Switch from SQLite first:
  ```bash
  uvicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
  ```

### AI

- [ ] **Switch to a production embedding model** — nomic-embed-text is good.
  For production: OpenAI text-embedding-3-small (better quality, pay per use).

- [ ] **Implement response caching for AI** — Same questions get same answers.
  Hash the (question + top_k chunk IDs) → cache LLM response for 24 hours.

---

## Monitoring Checklist

- [ ] **Set up Prometheus + Grafana** — Instrument your FastAPI app:
  ```bash
  pip install prometheus-fastapi-instrumentator
  from prometheus_fastapi_instrumentator import Instrumentator
  Instrumentator().instrument(app).expose(app)
  ```
  Dashboard at: localhost:3000 (Grafana)

- [ ] **Error alerting** — Get paged when things break:
  - Sentry for Python exceptions: `pip install sentry-sdk[fastapi]`
  - PagerDuty or OpsGenie for on-call rotation
  - Slack alerts for critical errors

- [ ] **Uptime monitoring** — Know before your customers do:
  - UptimeRobot (free tier): checks every 5 minutes, emails on downtime
  - Better Uptime or Pingdom for more features
  - Monitor both /health (backend) and the Streamlit URL

- [ ] **Log aggregation** — Ship logs to a central service:
  - Self-hosted: ELK stack (Elasticsearch + Logstash + Kibana)
  - Managed: Datadog, Papertrail, Logtail
  ```python
  import structlog  # Structured logging — JSON format, searchable
  logger = structlog.get_logger()
  logger.info("chat_request", tenant_id=tenant_id, tokens=input_tokens)
  ```

- [ ] **Set up health check dashboard** — Track:
  - API response time (P50, P95, P99)
  - Error rate (target: <1%)
  - Ollama/LLM response time
  - Database query time
  - Active WebSocket connections

---

## Legal Checklist

- [ ] **Terms of Service** — Required for any commercial product. Minimum sections:
  - What the service does and doesn't do
  - User responsibilities (they own their data)
  - Prohibited uses (illegal content, abuse)
  - Termination clause
  - Limitation of liability
  - Governing law / jurisdiction
  Use a service like Termly, Termsfeed, or hire a lawyer for custom ToS.

- [ ] **Privacy Policy** — Required by GDPR, CCPA, and most platforms:
  - What data you collect (emails, documents, usage logs)
  - How you use it (service operation, billing)
  - Data retention period
  - User rights (access, deletion, portability)
  - Cookie policy (if using cookies)
  - Contact: privacy@yourdomain.com

- [ ] **GDPR compliance (if serving EU users)**:
  - [ ] Right to erasure: implement DELETE /users/me that removes all user data
  - [ ] Data portability: implement GET /users/me/export that returns all user data
  - [ ] Consent: get explicit consent for marketing emails
  - [ ] Data Processing Agreement (DPA) with Ollama/OpenAI if using cloud LLMs
  - [ ] Appoint a Data Protection Officer if processing large amounts of EU data

- [ ] **CCPA compliance (if serving California users)**:
  - [ ] "Do Not Sell My Personal Information" link/mechanism
  - [ ] Privacy notice at collection point

- [ ] **Acceptable Use Policy (AUP)** — Define what users cannot do:
  - No illegal content (copyright infringement, CSAM, etc.)
  - No abuse of the API (excessive scraping, reselling access)
  - No reverse engineering

- [ ] **AI-specific disclosures** — Be clear that:
  - Responses are AI-generated and may be incorrect
  - Documents are processed by AI models
  - If using cloud LLMs: data may be sent to third parties

---

## Marketing Checklist

- [ ] **Landing page** — Minimum viable:
  - Hero: "Ask your documents anything" + screenshot
  - Problem: "Tired of Ctrl+F through 500-page PDFs?"
  - Solution: 3 bullets of what the product does
  - Social proof: testimonials (even from beta users)
  - Pricing table: Free / Pro / Enterprise
  - CTA: "Start free" button

- [ ] **SEO basics**:
  - Title tag: "AskMyDocs Pro — AI-Powered Document Q&A"
  - Meta description: 150 characters describing the product
  - robots.txt and sitemap.xml
  - Page load speed <3 seconds (check with PageSpeed Insights)

- [ ] **Demo video** — Record a 2-3 minute screen recording showing:
  1. Upload a PDF document
  2. Ask a natural language question
  3. Get a sourced, accurate answer
  Use Loom (free) for quick recording. Host on YouTube, embed on landing page.

- [ ] **ProductHunt launch preparation**:
  - Create a Maker account and claim your product
  - Prepare 5-sentence tagline and description
  - Prepare gallery (5 screenshots + 1 video)
  - Schedule launch for Tuesday-Thursday (most traffic)
  - Line up 20+ supporters to upvote on launch day
  - Prepare a "launch deal" (e.g., 30% off for PH users)

- [ ] **Email list** — Collect emails before launch:
  - Add an email capture to the landing page ("Notify me when we launch")
  - Use Mailchimp, ConvertKit, or Resend for email management

- [ ] **Distribution channels**:
  - [ ] Hacker News "Show HN" post (Monday morning 8am EST for most visibility)
  - [ ] Reddit: r/SaaS, r/MachineLearning, r/artificial (read rules first)
  - [ ] LinkedIn post: "I built an AI document Q&A tool, here's how..."
  - [ ] Twitter/X: share screenshots + link
  - [ ] Relevant Slack communities and Discord servers

---

## Quick-Start Summary

**Day 0 (Critical):**
1. Change all secrets
2. Enable HTTPS
3. Set up error monitoring (Sentry, 10 minutes to set up)
4. Add database backups

**Week 1 (Important):**
5. Add rate limiting
6. Set up uptime monitoring
7. Write ToS + Privacy Policy
8. Add database indexes

**Week 2-4 (Optimize):**
9. Switch to PostgreSQL
10. Add Prometheus + Grafana
11. Move document processing to background tasks
12. Launch marketing

---

*Last updated: May 2026 | AskMyDocs Pro v1.0*
