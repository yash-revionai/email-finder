# Email Finder — CLAUDE.md

Personal in-house B2B email finder tool. Input: first name, last name, company domain. Output: verified business email + confidence score + reason code. ~2k-3k lookups/week. Single user, VPS deployment.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Job queue | ARQ + Redis (async-native, replaces Celery) |
| Database | PostgreSQL + SQLModel + Alembic |
| Search | Exa AI API |
| Scraping | Firecrawl API |
| Verifier | OmniVerifier (primary) + stubs for MillionVerifier, NeverBounce, ZeroBounce, Reoon |
| Frontend | React 18 + Vite + Tailwind CSS |
| UI components | Tremor (charts + data display, Tailwind-native) |
| Auth | JWT (single user) |
| Packaging | Docker Compose |
| Reverse proxy | Nginx |

---

## Project Structure

```
email-finder/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── lookup.py        # POST /api/lookup, GET /api/lookup/{id}
│   │   │       ├── history.py       # GET /api/history
│   │   │       └── analytics.py     # GET /api/analytics/*
│   │   ├── core/
│   │   │   ├── config.py            # pydantic-settings, reads .env
│   │   │   ├── database.py          # SQLModel engine + session
│   │   │   └── security.py          # JWT auth
│   │   ├── models/                  # SQLModel models (ORM + Pydantic unified)
│   │   │   ├── lookup.py
│   │   │   ├── domain_pattern.py
│   │   │   └── verifier_call.py
│   │   ├── services/
│   │   │   ├── email_finder.py      # Main orchestration logic
│   │   │   ├── pattern_engine.py    # Generates + ranks email patterns
│   │   │   ├── catch_all_probe.py   # SMTP catch-all detection
│   │   │   ├── exa_searcher.py      # Exa AI integration
│   │   │   ├── firecrawl_scraper.py # Firecrawl integration
│   │   │   └── verifiers/
│   │   │       ├── base.py          # Abstract base class
│   │   │       ├── omniverifier.py  # Fully implemented
│   │   │       ├── milliverifier.py # Stub
│   │   │       ├── neverbounce.py   # Stub
│   │   │       ├── zerobounce.py    # Stub
│   │   │       └── reoon.py         # Stub
│   │   └── workers/
│   │       └── tasks.py             # ARQ worker tasks
│   ├── alembic/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LookupForm.tsx
│   │   │   ├── ResultCard.tsx
│   │   │   └── HistoryTable.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx        # Lookup form + live result
│   │   │   ├── History.tsx          # Filterable table + CSV export
│   │   │   └── Analytics.tsx        # Charts: volume, hit rate, credits
│   │   └── App.tsx
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── .env.example
```

---

## Core Lookup Pipeline

Every lookup goes through this sequence (executed as an ARQ background job):

1. **Cache check** — look up `domain_patterns` for a cached catch-all flag
2. **Catch-all probe** — if unknown, run SMTP probe against domain; if catch-all, return immediately (`reason_code: catch_all`, no verifier call)
3. **Exa AI search** — search `"firstname lastname @domain.com"` and extract candidate emails
4. **Firecrawl scrape** — scrape company `/team`, `/about`, `/contact` pages, extract email patterns found in HTML
5. **Pattern engine** — generate candidates from predefined global list, weighted by domain success history from `domain_patterns`
6. **Rank candidates** — merge and rank all candidates by confidence score
7. **OmniVerifier call #1** — highest confidence candidate; if valid → done
8. **OmniVerifier call #2** — if #1 invalid; if valid → done
9. **OmniVerifier call #3** — if #2 invalid; if valid → done
10. **`not_found`** — if all 3 fail
11. **Update `domain_patterns`** — record which pattern succeeded (learning layer)

**Hard limit:** maximum 3 verifier calls per lookup, sent 1 at a time. Never send 2 simultaneously.

---

## Database Schema

### `lookups`
```
id              UUID PK
first_name      text
last_name       text
domain          text
email           text (nullable)
confidence      float (0.0–1.0)
reason_code     text  -- valid | catch_all | invalid | not_found
verifier_calls_used  int (0–3)
status          text  -- pending | processing | done | failed
created_at      timestamp
completed_at    timestamp (nullable)
```

### `domain_patterns`
```
id                      UUID PK
domain                  text UNIQUE
is_catch_all            bool (nullable = unknown)
patterns                jsonb  -- [{pattern, confidence, success_count, total_count}]
last_successful_pattern text (nullable)
updated_at              timestamp
```

### `verifier_calls`
```
id          UUID PK
lookup_id   UUID FK → lookups
email       text
verifier    text  -- omniverifier | milliverifier | etc
result      text  -- valid | invalid | catch_all | unknown
credits_used int (default 1)
called_at   timestamp
```

---

## Pattern Engine

15 patterns ranked by global frequency (index 0 = highest global hit rate):

```python
PATTERNS = [
    "{first}.{last}",    # john.doe
    "{first}{last}",     # johndoe
    "{f}{last}",         # jdoe
    "{first}",           # john
    "{f}.{last}",        # j.doe
    "{first}_{last}",    # john_doe
    "{last}.{first}",    # doe.john
    "{last}{f}",         # doej
    "{first}{l}",        # johnd
    "{f}{l}",            # jd
    "{last}",            # doe
    "{first}-{last}",    # john-doe
    "{first}.{l}",       # john.d
    "{f}_{last}",        # j_doe
    "{last}_{first}",    # doe_john
]
```

Confidence formula: `global_weight[i] × domain_success_rate` where `domain_success_rate` comes from `domain_patterns.patterns` JSONB for the domain.

---

## Confidence Scoring

| Source | Base confidence |
|---|---|
| OmniVerifier: valid | 0.90–1.00 |
| Exa AI direct hit | 0.85 |
| Firecrawl scraped | 0.80 |
| Pattern #1 (no domain history) | 0.70 |
| Pattern #15 (no domain history) | 0.30 |
| Catch-all domain | 0.50 (returned as-is, no verification) |

**Reason codes:** `valid`, `catch_all`, `invalid`, `not_found`, `exa_found`, `scraped`, `pattern_derived`

---

## Frontend Pages

### Dashboard (`/`)
- Three-field lookup form: first name, last name, domain
- Submits to `POST /api/lookup`, polls `GET /api/lookup/{id}` via TanStack Query until `status === done`
- Result card: email, confidence progress bar, reason badge, verifier calls used

### History (`/history`)
- Sortable/filterable table of all lookups
- Columns: name, domain, email, confidence, reason, date
- CSV export button

### Analytics (`/analytics`)
- Weekly lookup volume (Tremor BarChart)
- Top domains by hit rate (Tremor BarChart horizontal)
- Verifier credits used over time (Tremor AreaChart)
- Summary stat cards: total lookups, overall hit rate, credits used this month

---

## Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@db:5432/emailfinder
REDIS_URL=redis://redis:6379/0
EXA_API_KEY=
FIRECRAWL_API_KEY=
OMNIVERIFIER_API_KEY=
JWT_SECRET=
```

---

## Decisions — Do Not Revisit

- **PostgreSQL** — not SQLite
- **ARQ** — not Celery (async-native, simpler config)
- **SQLModel** — not separate SQLAlchemy + Pydantic schemas
- **Tremor** — not raw Recharts
- **No SMTP verification engine** — we use OmniVerifier (and 4 other supported verifiers)
- **No Google scraping** — Exa AI + Firecrawl only
- **No overage pricing** — this is an internal tool
- **Max 3 verifier calls, 1 at a time** — never parallel, never more than 3
- **All 5 verifiers kept** — OmniVerifier wired up, others are stubs ready to activate
- **Exa + Firecrawl replace Bing/Brave** — user has keys for these, no Bing/Brave keys

---

## Phases

### Phase 1 — Backend Foundation
**API keys needed:** None
**Files to create:**
- `backend/requirements.txt` — all Python dependencies
- `backend/Dockerfile`
- `backend/app/main.py` — FastAPI app, router registration, lifespan
- `backend/app/core/config.py` — pydantic-settings reading `.env`
- `backend/app/core/database.py` — SQLModel engine, session dependency, `create_db_and_tables()`
- `backend/app/models/lookup.py` — Lookup SQLModel table
- `backend/app/models/domain_pattern.py` — DomainPattern SQLModel table
- `backend/app/models/verifier_call.py` — VerifierCall SQLModel table
- `backend/alembic.ini` + `backend/alembic/env.py` — migration setup
- `backend/alembic/versions/001_initial.py` — initial migration (all 3 tables)

**Deliverable:** `uvicorn app.main:app` starts, `GET /health` returns `{"status": "ok"}`, tables exist in DB.

---

### Phase 2 — Core Logic
**API keys needed:** None
**Files to create:**
- `backend/app/services/pattern_engine.py`
  - `PATTERNS` list (15 entries)
  - `global_weight(index)` → float
  - `generate_candidates(first, last, domain, domain_patterns_row)` → list of `(email, confidence)` sorted desc
- `backend/app/services/catch_all_probe.py`
  - `is_catch_all(domain)` → bool — SMTP probe using a random address
  - Result cached to `domain_patterns.is_catch_all`
- `backend/app/workers/tasks.py`
  - ARQ `WorkerSettings` with Redis URL from config
  - `run_lookup(ctx, lookup_id)` — stub that sets status to `processing` then `done`
  - `startup(ctx)` / `shutdown(ctx)` hooks for DB session

**Deliverable:** ARQ worker starts (`arq app.workers.tasks.WorkerSettings`), pattern engine unit-testable in isolation.

---

### Phase 3 — External Integrations
**API keys needed:** `OMNIVERIFIER_API_KEY`, `EXA_API_KEY`, `FIRECRAWL_API_KEY`
**Files to create:**
- `backend/app/services/verifiers/base.py`
  - `VerifierResult` dataclass: `result`, `reason`, `credits_used`
  - `BaseVerifier` ABC with `async def verify(email) -> VerifierResult`
- `backend/app/services/verifiers/omniverifier.py` — full implementation against OmniVerifier API
- `backend/app/services/verifiers/milliverifier.py` — stub (raises `NotImplementedError`)
- `backend/app/services/verifiers/neverbounce.py` — stub
- `backend/app/services/verifiers/zerobounce.py` — stub
- `backend/app/services/verifiers/reoon.py` — stub
- `backend/app/services/exa_searcher.py`
  - `search_email(first, last, domain)` → list of candidate emails extracted from Exa results
- `backend/app/services/firecrawl_scraper.py`
  - `scrape_domain_patterns(domain)` → list of emails found on `/about`, `/team`, `/contact` pages

**Deliverable:** Each integration independently testable with real API keys.

---

### Phase 4 — Orchestration + API
**API keys needed:** All from Phase 3 (already set)
**Files to create:**
- `backend/app/services/email_finder.py`
  - `run_email_finder(lookup_id, db)` — full 11-step pipeline
  - Calls catch_all_probe → exa_searcher → firecrawl_scraper → pattern_engine → verifier loop (max 3, 1 at a time) → update domain_patterns
- `backend/app/workers/tasks.py` — replace stub with real `run_lookup` call to `email_finder.run_email_finder`
- `backend/app/api/routes/lookup.py`
  - `POST /api/lookup` — create Lookup row (status=pending), enqueue ARQ job, return `{id, status}`
  - `GET /api/lookup/{id}` — return current lookup row
- `backend/app/api/routes/history.py`
  - `GET /api/history?page=&limit=&domain=&status=` — paginated lookup history
- `backend/app/api/routes/analytics.py`
  - `GET /api/analytics/summary` — total lookups, hit rate, credits used this month
  - `GET /api/analytics/volume` — weekly lookup counts (last 12 weeks)
  - `GET /api/analytics/domains` — top 10 domains by hit rate
  - `GET /api/analytics/credits` — verifier credits used per week (last 12 weeks)

**Deliverable:** Full end-to-end lookup via `curl POST /api/lookup` completes and returns a verified email.

---

### Phase 5 — Frontend
**API keys needed:** None
**Files to create:**
- `frontend/package.json` — React 18, Vite, Tailwind, Tremor, TanStack Query, React Router
- `frontend/src/App.tsx` — router (Dashboard `/`, History `/history`, Analytics `/analytics`)
- `frontend/src/lib/api.ts` — typed fetch wrappers for all backend endpoints
- `frontend/src/pages/Dashboard.tsx`
  - `LookupForm` — first name, last name, domain fields + submit
  - Polls `GET /api/lookup/{id}` every 1.5s via TanStack Query until `status === done`
  - `ResultCard` — email, confidence bar, reason badge, verifier calls used
- `frontend/src/pages/History.tsx`
  - `HistoryTable` — sortable columns, domain/status filter, CSV export
- `frontend/src/pages/Analytics.tsx`
  - Tremor stat cards: total lookups, hit rate, credits this month
  - Tremor `BarChart` — weekly lookup volume
  - Tremor `BarChart` horizontal — top domains by hit rate
  - Tremor `AreaChart` — credits used per week
- `frontend/Dockerfile`

**Deliverable:** `npm run dev` shows all 3 pages; lookup form submits and displays result live.

---

### Phase 6 — Infrastructure + Auth
**API keys needed:** None
**Files to create:**
- `backend/app/core/security.py`
  - `create_access_token(data)` → JWT string
  - `get_current_user` FastAPI dependency — validates Bearer token
  - `POST /api/auth/token` route — accepts `password` from env, returns JWT
- Apply `get_current_user` dependency to all non-auth routes
- `docker-compose.yml` — services: `backend`, `worker` (ARQ), `frontend`, `db` (postgres), `redis`, `nginx`
- `nginx/nginx.conf` — proxy `/api/*` → backend:8000, `/*` → frontend:3000
- `.env.example` — all required variables with placeholder values
- `frontend/src/lib/auth.ts` — store JWT in localStorage, attach to requests, redirect to login if 401
- `frontend/src/pages/Login.tsx` — password field, calls `/api/auth/token`, stores token

**Deliverable:** `docker-compose up` on a fresh VPS, app fully functional behind Nginx with JWT auth.
