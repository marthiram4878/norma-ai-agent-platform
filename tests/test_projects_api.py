"""Project / knowledge-space HTTP contract tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.projects import get_project_service
from app.api.v1.workflows import get_workflow_service
from app.main import app
from app.services.projects import SpaceNotFound
from tests.auth_helpers import authenticated_client


class FakeSpace:
    def __init__(self) -> None:
        self.id = uuid4()
        self.project_id = uuid4()
        self.name = "Main"
        self.created_at = datetime.now(UTC)


class FakeProject:
    def __init__(self) -> None:
        self.id = uuid4()
        self.workspace_id = uuid4()
        self.name = "My project"
        self.created_at = datetime.now(UTC)
        self.spaces = [FakeSpace()]
        self.spaces[0].project_id = self.id


class FakeProjectService:
    def __init__(self) -> None:
        self.project = FakeProject()

    async def ensure_defaults(self, **_: object) -> FakeProject:
        return self.project

    async def list_projects(self, **_: object) -> list[FakeProject]:
        return [self.project]

    async def create_project(self, **kwargs: object) -> FakeProject:
        project = FakeProject()
        project.name = str(kwargs["name"])
        project.workspace_id = kwargs["workspace_id"]  # type: ignore[assignment]
        return project


def test_list_projects_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/projects",
            params={"workspace_id": str(uuid4())},
        )
    assert response.status_code == 401


def test_list_projects_contract() -> None:
    service = FakeProjectService()
    app.dependency_overrides[get_project_service] = lambda: service
    try:
        with authenticated_client("app.api.v1.projects"):
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/projects",
                    params={"workspace_id": str(service.project.workspace_id)},
                )
    finally:
        app.dependency_overrides.pop(get_project_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["name"] == "My project"
    assert payload[0]["spaces"][0]["name"] == "Main"


def test_create_project_contract() -> None:
    service = FakeProjectService()
    app.dependency_overrides[get_project_service] = lambda: service
    try:
        with authenticated_client("app.api.v1.projects"):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/projects",
                    json={
                        "workspace_id": str(uuid4()),
                        "name": "Launch ops",
                    },
                )
    finally:
        app.dependency_overrides.pop(get_project_service, None)

    assert response.status_code == 201
    assert response.json()["name"] == "Launch ops"


def test_unknown_space_returns_404_on_launch() -> None:
    app.dependency_overrides[get_workflow_service] = lambda: AsyncMock()
    try:
        with authenticated_client("app.api.v1.workflows"):
            with patch("app.api.v1.workflows.ProjectService") as cls:
                projects = cls.return_value
                projects.require_space = AsyncMock(
                    side_effect=SpaceNotFound("Knowledge space not found")
                )
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/workflows/launch-strategy",
                        json={
                            "workspace_id": str(uuid4()),
                            "space_id": str(uuid4()),
                            "brief": "Open coffee shops in Australia",
                        },
                    )
    finally:
        app.dependency_overrides.pop(get_workflow_service, None)

    assert response.status_code == 404
