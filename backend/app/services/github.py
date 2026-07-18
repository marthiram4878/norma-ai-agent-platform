"""GitHub OAuth, repo listing, and markdown export for knowledge ingest."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.integration_models import IntegrationConnection
from app.services.token_crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)

GITHUB_PROVIDER = "github"
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"
GITHUB_SCOPES = "read:user repo"
STATE_TYPE = "github_oauth"
MAX_REPOS_LIST = 50
MAX_MARKDOWN_FILES = 20
MAX_FILE_BYTES = 1_000_000


class GitHubConfigurationError(RuntimeError):
    pass


class GitHubNotConnected(LookupError):
    pass


class GitHubAPIError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GitHubRepoSummary:
    id: int
    full_name: str
    private: bool
    default_branch: str


@dataclass(frozen=True, slots=True)
class GitHubOAuthState:
    user_id: UUID
    workspace_id: UUID
    space_id: UUID


@dataclass(frozen=True, slots=True)
class GitHubMarkdownFile:
    path: str
    filename: str
    content: str


def _require_oauth_config() -> tuple[str, str]:
    client_id = settings.github_client_id
    secret = settings.github_client_secret
    if not client_id or secret is None or not secret.get_secret_value():
        raise GitHubConfigurationError("GitHub OAuth is not configured")
    return client_id, secret.get_secret_value()


def create_oauth_state(
    *,
    user_id: UUID,
    workspace_id: UUID,
    space_id: UUID,
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "type": STATE_TYPE,
            "sub": str(user_id),
            "workspace_id": str(workspace_id),
            "space_id": str(space_id),
            "nonce": str(uuid4()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def parse_oauth_state(token: str) -> GitHubOAuthState:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid OAuth state") from exc
    if payload.get("type") != STATE_TYPE:
        raise ValueError("Invalid OAuth state type")
    return GitHubOAuthState(
        user_id=UUID(str(payload["sub"])),
        workspace_id=UUID(str(payload["workspace_id"])),
        space_id=UUID(str(payload["space_id"])),
    )


def build_authorize_url(*, state: str) -> str:
    client_id, _ = _require_oauth_config()
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": GITHUB_SCOPES,
            "state": state,
        }
    )
    return f"{GITHUB_AUTHORIZE_URL}?{query}"


class GitHubClient:
    """Thin GitHub HTTP client used by the application service."""

    def __init__(
        self,
        access_token: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.access_token = access_token
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> GitHubClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        allow_404: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        assert self._client is not None
        response = await self._client.request(
            method,
            f"{GITHUB_API}{path}",
            headers=self._headers(),
            **kwargs,
        )
        if allow_404 and response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API {response.status_code}: {response.text[:300]}"
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def get_user(self) -> dict[str, Any]:
        payload = await self._request("GET", "/user")
        assert isinstance(payload, dict)
        return payload

    async def list_repos(
        self, *, limit: int = MAX_REPOS_LIST
    ) -> list[GitHubRepoSummary]:
        payload = await self._request(
            "GET",
            "/user/repos",
            params={
                "per_page": min(limit, 100),
                "sort": "updated",
                "affiliation": "owner,collaborator,organization_member",
            },
        )
        assert isinstance(payload, list)
        results: list[GitHubRepoSummary] = []
        for item in payload[:limit]:
            if not isinstance(item, dict):
                continue
            results.append(
                GitHubRepoSummary(
                    id=int(item["id"]),
                    full_name=str(item["full_name"]),
                    private=bool(item.get("private")),
                    default_branch=str(item.get("default_branch") or "main"),
                )
            )
        return results

    async def export_repo_markdown(
        self, full_name: str
    ) -> list[GitHubMarkdownFile]:
        owner, _, repo = full_name.partition("/")
        if not owner or not repo:
            raise GitHubAPIError(f"Invalid repository name: {full_name}")

        files: list[GitHubMarkdownFile] = []
        seen_paths: set[str] = set()

        readme = await self._request(
            "GET", f"/repos/{owner}/{repo}/readme", allow_404=True
        )
        if isinstance(readme, dict):
            content = _decode_content(readme)
            path = str(readme.get("path") or "README.md")
            if content is not None:
                seen_paths.add(path)
                files.append(
                    GitHubMarkdownFile(
                        path=path,
                        filename=_ingest_filename(owner, repo, path),
                        content=content,
                    )
                )

        repo_payload = await self._request("GET", f"/repos/{owner}/{repo}")
        assert isinstance(repo_payload, dict)
        default_branch = str(repo_payload.get("default_branch") or "main")
        branch = await self._request(
            "GET", f"/repos/{owner}/{repo}/branches/{default_branch}"
        )
        assert isinstance(branch, dict)
        sha = str((branch.get("commit") or {}).get("sha") or "")
        if not sha:
            return files

        tree_payload = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/trees/{sha}",
            params={"recursive": "1"},
        )
        assert isinstance(tree_payload, dict)
        md_paths: list[str] = []
        for entry in tree_payload.get("tree") or []:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") != "blob":
                continue
            path = str(entry.get("path") or "")
            if not _is_markdown_path(path):
                continue
            if path in seen_paths:
                continue
            size = int(entry.get("size") or 0)
            if size > MAX_FILE_BYTES:
                continue
            md_paths.append(path)
            if len(md_paths) >= MAX_MARKDOWN_FILES:
                break

        for path in md_paths:
            content_payload = await self._request(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}",
                allow_404=True,
            )
            if not isinstance(content_payload, dict):
                continue
            content = _decode_content(content_payload)
            if content is None:
                continue
            files.append(
                GitHubMarkdownFile(
                    path=path,
                    filename=_ingest_filename(owner, repo, path),
                    content=content,
                )
            )

        return files


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    client_id, client_secret = _require_oauth_config()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
        )
    if response.status_code >= 400:
        raise GitHubAPIError(
            "GitHub token exchange failed: "
            f"{response.status_code} {response.text[:300]}"
        )
    payload = response.json()
    if payload.get("error"):
        detail = payload.get("error_description") or payload.get("error")
        raise GitHubAPIError(f"GitHub token exchange failed: {detail}")
    if not payload.get("access_token"):
        raise GitHubAPIError("GitHub token exchange returned no access_token")
    return payload


class GitHubIntegrationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_connection(
        self, *, user_id: UUID, workspace_id: UUID
    ) -> IntegrationConnection | None:
        return await self.session.scalar(
            select(IntegrationConnection).where(
                IntegrationConnection.provider == GITHUB_PROVIDER,
                IntegrationConnection.user_id == user_id,
                IntegrationConnection.workspace_id == workspace_id,
            )
        )

    async def upsert_connection(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        access_token: str,
        external_workspace_id: str | None,
        external_workspace_name: str | None,
    ) -> IntegrationConnection:
        existing = await self.get_connection(
            user_id=user_id, workspace_id=workspace_id
        )
        encrypted = encrypt_secret(access_token)
        if existing is None:
            existing = IntegrationConnection(
                provider=GITHUB_PROVIDER,
                user_id=user_id,
                workspace_id=workspace_id,
                access_token_encrypted=encrypted,
                external_workspace_id=external_workspace_id,
                external_workspace_name=external_workspace_name,
            )
            self.session.add(existing)
        else:
            existing.access_token_encrypted = encrypted
            existing.external_workspace_id = external_workspace_id
            existing.external_workspace_name = external_workspace_name
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def disconnect(self, *, user_id: UUID, workspace_id: UUID) -> None:
        connection = await self.get_connection(
            user_id=user_id, workspace_id=workspace_id
        )
        if connection is None:
            raise GitHubNotConnected("GitHub is not connected")
        await self.session.delete(connection)
        await self.session.commit()

    async def access_token(self, *, user_id: UUID, workspace_id: UUID) -> str:
        connection = await self.get_connection(
            user_id=user_id, workspace_id=workspace_id
        )
        if connection is None:
            raise GitHubNotConnected("GitHub is not connected")
        return decrypt_secret(connection.access_token_encrypted)


def _is_markdown_path(path: str) -> bool:
    lower = path.lower()
    return lower.endswith(".md") or lower.endswith(".markdown")


def _decode_content(payload: dict[str, Any]) -> str | None:
    encoding = payload.get("encoding")
    raw = payload.get("content")
    if encoding != "base64" or not isinstance(raw, str):
        return None
    try:
        data = base64.b64decode(raw)
    except Exception:
        return None
    if len(data) > MAX_FILE_BYTES:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return (cleaned.strip("-") or "file")[:80]


def _ingest_filename(owner: str, repo: str, path: str) -> str:
    return f"github-{_slug(owner)}-{_slug(repo)}-{_slug(path)}.md"
