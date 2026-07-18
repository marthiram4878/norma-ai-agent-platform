"""Workflow HTTP contract tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.workflows import get_workflow_service
from app.database.workflow_models import WorkflowRun, WorkflowStatus
from app.main import app
from app.workflows.launch_strategy import LaunchStrategyWorkflow
from tests.auth_helpers import authenticated_client


class FakeLaunchStrategyService:
    def __init__(self) -> None:
        self.run_id = uuid4()
        self.enqueued: list[dict[str, object]] = []

    async def enqueue(self, **kwargs: object) -> WorkflowRun:
        self.enqueued.append(kwargs)
        workspace_id = kwargs["workspace_id"]
        return WorkflowRun(
            id=self.run_id,
            workspace_id=workspace_id,  # type: ignore[arg-type]
            space_id=kwargs["space_id"],  # type: ignore[arg-type]
            user_id=kwargs["user_id"],  # type: ignore[arg-type]
            workflow_type=LaunchStrategyWorkflow.WORKFLOW_TYPE,
            status=WorkflowStatus.PENDING,
            brief=str(kwargs["brief"]),
            product_name=kwargs.get("product_name"),  # type: ignore[arg-type]
            current_step=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            artifacts=[],
        )

    async def list_runs(self, **kwargs: object) -> list[WorkflowRun]:
        return []

    async def get_run(self, **kwargs: object) -> WorkflowRun:
        raise LookupError("not found")


def test_launch_strategy_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/workflows/launch-strategy",
            json={
                "workspace_id": str(uuid4()),
                "brief": "Open coffee shops in Australia",
            },
        )
    assert response.status_code == 401


def test_launch_strategy_enqueues_async() -> None:
    service = FakeLaunchStrategyService()
    space_id = uuid4()
    app.dependency_overrides[get_workflow_service] = lambda: service
    try:
        with authenticated_client("app.api.v1.workflows"):
            with patch(
                "app.api.v1.workflows.ProjectService"
            ) as project_service_cls:
                projects = project_service_cls.return_value
                projects.default_space_id = AsyncMock(return_value=space_id)
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/workflows/launch-strategy",
                        json={
                            "workspace_id": str(uuid4()),
                            "brief": "Open coffee shops in Australia",
                            "product_name": "Aussie Roast",
                        },
                    )
    finally:
        app.dependency_overrides.pop(get_workflow_service, None)

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["product_name"] == "Aussie Roast"
    assert payload["artifacts"] == []
    assert service.enqueued[0]["space_id"] == space_id


def test_list_workflow_runs_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/workflows/runs",
            params={"workspace_id": str(uuid4())},
        )
    assert response.status_code == 401


def test_get_workflow_run_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workflows/runs/{uuid4()}",
            params={"workspace_id": str(uuid4())},
        )
    assert response.status_code == 401
