# AI Knowledge Inbox

Save notes or URLs, ask questions over everything saved. RAG pipeline (chunk → embed → retrieve → generate) with cited sources. Single-user, no auth.

## Tech stack

**Backend:** Python, FastAPI, SQLite, SQLAlchemy, OpenAI (`text-embedding-3-small`, `gpt-4o-mini`)
**Frontend:** React 18, TypeScript, Vite, Tailwind CSS v4, Zustand, axios

## Setup

Requires Python 3.11+, Node 18+, and an OpenAI API key with billing enabled.

### Backend

**macOS / Linux:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set OPENAI_API_KEY in .env
uvicorn app.main:app --reload
```

**Windows (Command Prompt):**

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

If PowerShell blocks the activation script with an execution-policy error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, then retry.

Edit `.env` and set `OPENAI_API_KEY` before starting the server, on any OS. Runs at `http://localhost:8000`. Interactive API docs at `/docs`.

### Frontend

Same commands on every OS (pnpm/npm handle the platform differences internally):

```bash
cd frontend
pnpm install     # or npm install
```

Copy `.env.example` to `.env` (`cp .env.example .env` on macOS/Linux, `copy .env.example .env` on Windows CMD, `Copy-Item .env.example .env` on PowerShell), then:

```bash
pnpm start
```

Runs at `http://localhost:3000`.

### Tests

```bash
cd backend
# activate the venv as above for your OS, then:
python -m pytest tests/ -v
```

29 tests. Unit tests cover pure-function services and Pydantic validation directly, no mocking needed:

- `test_chunking.py` — window sizing, overlap boundary preservation, empty input, invalid config
- `test_embeddings.py` — cosine similarity properties (identical/orthogonal/opposite vectors, scale invariance, zero-vector guard)
- `test_schemas.py` — request validation (required fields per source type, whitespace stripping, question length limits)

API integration tests use FastAPI's `TestClient` against an isolated per-test SQLite database (via `conftest.py`, dependency-overridden `get_db`), with OpenAI calls mocked so the suite is fast, free, and deterministic:

- `test_api_items.py` — ingest note/URL success, validation errors, duplicate-URL 409, unreachable-URL 422, list ordering, delete then 404 on re-delete
- `test_api_query.py` — empty-question rejection, no-saved-content fallback, and the full save → ask pipeline end to end (save a note, ask about it, verify the retrieved source matches the saved item)

Not covered: real (non-mocked) calls to OpenAI or live URL fetching — those were verified manually against a running server during development.

**Frontend** has no separate unit test suite. Its logic is thin (display formatting, simple UI state) compared to the backend's actual RAG/system-design surface, so correctness there is enforced via TypeScript's type checker and the linter instead:

```bash
cd frontend
pnpm run typecheck   # tsc --noEmit
pnpm run lint         # oxlint
```

Both run clean. `pnpm run build` runs the typecheck as a build gate before bundling, so a type error can't ship silently.

## System design

```
backend/app/
├── api/        # HTTP routes only — parse request, call a service, map result to a status code
├── services/   # chunking, embeddings, retrieval, answering, ingestion, suggestions
├── db/         # SQLAlchemy models, session/engine setup
├── core/       # config, structured logging
└── main.py

frontend/src/
├── api/        # axios client, one function per endpoint
├── store/      # Zustand — all shared state and API-calling logic
├── components/ # one component per file, presentational
└── App.tsx     # layout only
```

Routes contain no business logic. Ingestion pipeline: fetch (URL only) → chunk → embed (batched) → single atomic transaction for item + all chunks. Query pipeline: embed question → cosine-similarity scan over stored chunks → filter by minimum similarity → top-k → grounded LLM prompt with numbered context → answer + cited sources.

## API

| Method | Path | Notes |
|---|---|---|
| `POST` | `/ingest` | `201`; `409` duplicate URL; `422` bad input/unreachable URL |
| `GET` | `/items` | Newest first |
| `DELETE` | `/items/{id}` | `204`; cascades to chunks |
| `POST` | `/query` | Grounded answer + cited sources |
| `GET` | `/health` | Health check |

## Tradeoffs

**Chunking** — character-based sliding window, 1200 chars, 150 overlap. Simple, no dependencies. Overlap prevents boundary sentences from being permanently split. Token-based or semantic chunking would be more precise; not justified at this scale.

**Vector storage** — SQLite, embeddings as JSON text, brute-force cosine similarity in Python. O(n) scan, sub-millisecond at hundreds of chunks. Breaks down two ways at scale: (1) O(n) scan cost, (2) every query loads all embeddings into app memory regardless of compute cost. Production fix: Postgres + pgvector, so the database does the search and returns only top-k.

**Retrieval threshold** — minimum cosine similarity (0.45) before a chunk is eligible, on top of top-k. Without it, retrieval always returns *something* even when nothing relevant was saved. Threshold value is a real tuning tradeoff (too low leaks noise, too high drops legitimate secondary sources), not a solved problem.

**Grounding** — system prompt restricts the LLM to the retrieved context and explicitly permits "I don't know." Reduces hallucination; doesn't eliminate it.

**Concurrency** — WAL mode (readers don't block on writers) + `busy_timeout` (writers wait instead of failing) + a partial unique index on `source_ref` for URL items (blocks the TOCTOU duplicate-save race at the DB level, not in application code) + one transaction per ingest (item + all chunks succeed or fail together).

**SQLite over Postgres** — matches the assignment's explicit guidance against overengineering infra; zero setup for a reviewer. Costs: no native vector type, single-writer locking, no real migrations. First things to change in production.

**Suggested questions generated at write time, not read time** — one extra LLM call per ingested item, cached and reused on every subsequent view instead of regenerated per page load. Best-effort: failure doesn't block the save.

## Production changes

- **Vector storage**: Postgres + pgvector for indexed similarity search.
- **Deployment**: SQLite-as-a-file needs a persistent-disk host (VPS, or a Render/Railway/Fly "web service"). Doesn't work on serverless (Vercel, Lambda) — filesystem isn't guaranteed to persist across invocations. Postgres removes this constraint.
- **Migrations**: Alembic instead of `create_all` + manual DB resets.
- **Idempotency**: `POST /ingest` isn't idempotent for notes (no uniqueness constraint, unlike URLs). Add a client-generated idempotency key.
- **URL extraction**: current tag-stripping heuristic can leak non-article content (e.g. non-semantic sidebar `<div>`s). A readability-extraction library would be more robust.
- **Prompt injection**: saved content is trusted input to the prompt today. Production needs to treat ingested content as untrusted.
- **Auth & rate limiting**: out of scope per assignment, required before multi-tenant use.

## Known limitations

- No frontend test suite (see Testing) — TypeScript + lint stand in instead.
- Mobile uses a two-tab switcher (Save / Ask) below 768px instead of showing both panels.
- `MIN_SIMILARITY`, `TOP_K_CHUNKS`, `CHUNK_SIZE_CHARS`, `CHUNK_OVERLAP_CHARS` are tunable via `.env`; checked-in values are starting points, not fixed constants.
