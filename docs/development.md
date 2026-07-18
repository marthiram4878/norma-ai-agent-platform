# Development

## Prerequisites

- Python 3.12
- Node.js 20+
- Docker + Docker Compose (for full stack)

## Backend

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# point DATABASE_URL / REDIS / QDRANT / EMBEDDINGS at local or compose services
alembic -c alembic.ini upgrade head
uvicorn app.main:app --app-dir backend --reload
pytest
ruff check backend tests
```

Worker (separate process):

```bash
python -m app.workers.main
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Default API base: `http://localhost:8000/api/v1` (`VITE_API_URL`).

## Layout

```text
backend/app/
  api/v1/       HTTP routers
  agents/       Agent implementations
  workflows/    LangGraph graphs
  services/     Application use cases
  rag/          Embeddings + retrieval adapters
  database/     SQLAlchemy models
  workers/      Redis consumers
frontend/       React + Vite + Tailwind
tests/          Pytest contracts and unit tests
docs/           Engineering documentation
```

## Conventions

- Prefer application services over fat routers  
- Keep provider SDKs behind adapters  
- New durable schema → Alembic migration  
- Async long work → Redis job + pollable resource  
- Tests under `tests/` with `pythonpath` set in `pyproject.toml`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for PR expectations.
