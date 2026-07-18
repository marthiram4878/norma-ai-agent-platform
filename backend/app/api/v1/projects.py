"""Project and knowledge-space endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_workspace_access
from app.database.auth_models import User
from app.database.session import get_db_session
from app.schemas.projects import (
    KnowledgeSpaceResponse,
    ProjectCreate,
    ProjectResponse,
    SpaceCreate,
)
from app.services.projects import ProjectNotFound, ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectService:
    return ProjectService(session)


def _project_response(project: object) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,  # type: ignore[attr-defined]
        workspace_id=project.workspace_id,  # type: ignore[attr-defined]
        name=project.name,  # type: ignore[attr-defined]
        created_at=project.created_at,  # type: ignore[attr-defined]
        spaces=[
            KnowledgeSpaceResponse(
                id=space.id,
                project_id=space.project_id,
                name=space.name,
                created_at=space.created_at,
            )
            for space in project.spaces  # type: ignore[attr-defined]
        ],
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[ProjectService, Depends(get_project_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ProjectResponse]:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    await service.ensure_defaults(workspace_id=workspace_id, user_id=user.id)
    await session.commit()
    projects = await service.list_projects(workspace_id=workspace_id)
    return [_project_response(project) for project in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    service: Annotated[ProjectService, Depends(get_project_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> ProjectResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    project = await service.create_project(
        workspace_id=payload.workspace_id,
        user_id=user.id,
        name=payload.name,
    )
    await session.commit()
    return _project_response(project)


@router.post(
    "/{project_id}/spaces",
    response_model=KnowledgeSpaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_space(
    project_id: UUID,
    payload: SpaceCreate,
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[ProjectService, Depends(get_project_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> KnowledgeSpaceResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        space = await service.create_space(
            project_id=project_id,
            workspace_id=workspace_id,
            name=payload.name,
        )
    except ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return KnowledgeSpaceResponse(
        id=space.id,
        project_id=space.project_id,
        name=space.name,
        created_at=space.created_at,
    )
