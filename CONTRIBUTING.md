# Contributing

Thanks for helping improve Norma AI.

## Before you start

1. Read [docs/architecture.md](docs/architecture.md) and [docs/development.md](docs/development.md).
2. Open an issue for large changes so scope can be aligned early.
3. Follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development loop

```bash
# backend
pip install -e ".[dev]"
pytest
ruff check backend tests

# frontend
cd frontend && npm install && npm run build
```

Prefer small, reviewable PRs with a clear “why”.

## Pull requests

- Keep API and schema changes documented (`docs/api.md`, OpenAPI).
- New durable tables → Alembic migration.
- Long-running work → Redis job + pollable status (do not block HTTP).
- Add or update tests for behavior you change.
- Do not commit secrets, `.env`, or local model caches.

## Commit messages

Use short, imperative subjects focused on intent, e.g.:

```text
Add async knowledge ingest worker path.
```

## Security

Do not file public issues for sensitive vulnerabilities. See [SECURITY.md](SECURITY.md).
