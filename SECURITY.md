# Security Policy

## Supported versions

The `main` branch is the actively maintained line for security fixes during the
MVP phase.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

Instead, email the maintainers using the address on the GitHub organization /
profile, or open a private security advisory on GitHub if enabled for this
repository.

Include:

- Description of the issue and impact
- Steps to reproduce
- Affected component (API route, worker, auth, etc.)
- Any suggested fix (optional)

We aim to acknowledge reports within a few business days.

## Security baseline (current)

- Secrets via environment variables (never commit `.env`)
- HttpOnly cookie JWTs; refresh tokens hashed at rest
- Workspace membership checks on tenant-scoped APIs
- Knowledge/memory retrieval filtered by `workspace_id` / `space_id`
- Worker and API process separation for long-running jobs

## Production hardening still required

Managed secret storage, rate limiting, audit logging, TLS termination, and
stricter tool/integration permissions before any public multi-tenant SaaS
deployment. See [docs/architecture.md](docs/architecture.md).
