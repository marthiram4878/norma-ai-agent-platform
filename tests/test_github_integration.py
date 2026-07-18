"""GitHub OAuth and import contract tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.integrations import get_github_service, get_knowledge_service
from app.main import app
from app.services.github import (
    GitHubMarkdownFile,
    GitHubRepoSummary,
    build_authorize_url,
    create_oauth_state,
    parse_oauth_state,
)
from app.services.knowledge import IndexedDocument
from tests.auth_helpers import authenticated_client


def test_github_oauth_state_roundtrip() -> None:
    user_id = uuid4()
    workspace_id = uuid4()
    space_id = uuid4()
    token = create_oauth_state(
        user_id=user_id, workspace_id=workspace_id, space_id=space_id
    )
    claims = parse_oauth_state(token)
    assert claims.user_id == user_id
    assert claims.workspace_id == workspace_id
    assert claims.space_id == space_id


def test_github_build_authorize_url_contains_client() -> None:
    with patch("app.services.github.settings") as settings:
        settings.github_client_id = "gh-client"
        settings.github_client_secret = type(
            "S", (), {"get_secret_value": lambda self: "secret"}
        )()
        settings.github_redirect_uri = (
            "http://localhost:8000/api/v1/integrations/github/callback"
        )
        url = build_authorize_url(state="abc")
    assert "client_id=gh-client" in url
    assert "state=abc" in url
    assert "scope=" in url


def test_github_authorize_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/integrations/github/authorize",
            params={"workspace_id": str(uuid4()), "space_id": str(uuid4())},
        )
    assert response.status_code == 401


def test_github_import_contract() -> None:
    workspace_id = uuid4()
    space_id = uuid4()
    document_id = uuid4()

    class FakeGitHubService:
        async def access_token(self, **_: object) -> str:
            return "github-token"

    class FakeKnowledge:
        async def enqueue(self, **kwargs: object) -> IndexedDocument:
            return IndexedDocument(
                id=document_id,
                workspace_id=kwargs["workspace_id"],  # type: ignore[arg-type]
                filename=str(kwargs["filename"]),
                content_type=str(kwargs["content_type"]),
                size_bytes=len(kwargs["data"]),  # type: ignore[arg-type]
                sha256="c" * 64,
                status="pending",
                chunk_count=0,
                created_at=datetime.now(UTC),
            )

    class FakeClient:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def export_repo_markdown(
            self, full_name: str
        ) -> list[GitHubMarkdownFile]:
            return [
                GitHubMarkdownFile(
                    path="README.md",
                    filename=f"github-{full_name.replace('/', '-')}-readme.md",
                    content=f"# {full_name}\n",
                )
            ]

    app.dependency_overrides[get_github_service] = FakeGitHubService
    app.dependency_overrides[get_knowledge_service] = FakeKnowledge
    try:
        with authenticated_client("app.api.v1.integrations"):
            with (
                patch("app.api.v1.integrations.ProjectService") as project_cls,
                patch("app.api.v1.integrations.GitHubClient", FakeClient),
            ):
                project_cls.return_value.require_space = AsyncMock()
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/integrations/github/import",
                        json={
                            "workspace_id": str(workspace_id),
                            "space_id": str(space_id),
                            "repo_full_names": ["acme/demo"],
                        },
                    )
    finally:
        app.dependency_overrides.pop(get_github_service, None)
        app.dependency_overrides.pop(get_knowledge_service, None)

    assert response.status_code == 202
    payload = response.json()
    assert payload["items"][0]["status"] == "pending"
    assert payload["items"][0]["document_id"] == str(document_id)
    assert payload["items"][0]["repo_full_name"] == "acme/demo"


def test_github_repos_lists_results() -> None:
    class FakeGitHubService:
        async def access_token(self, **_: object) -> str:
            return "github-token"

    class FakeClient:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def list_repos(self, **_: object) -> list[GitHubRepoSummary]:
            return [
                GitHubRepoSummary(
                    id=1,
                    full_name="acme/demo",
                    private=False,
                    default_branch="main",
                )
            ]

    app.dependency_overrides[get_github_service] = FakeGitHubService
    try:
        with authenticated_client("app.api.v1.integrations"):
            with patch("app.api.v1.integrations.GitHubClient", FakeClient):
                with TestClient(app) as client:
                    response = client.get(
                        "/api/v1/integrations/github/repos",
                        params={"workspace_id": str(uuid4())},
                    )
    finally:
        app.dependency_overrides.pop(get_github_service, None)

    assert response.status_code == 200
    assert response.json()[0]["full_name"] == "acme/demo"
