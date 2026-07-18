"""Third-party integration endpoints (Notion / GitHub OAuth + import)."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_workspace_access
from app.core.config import settings
from app.database.auth_models import User
from app.database.session import get_db_session
from app.schemas.integrations import (
    GitHubAuthorizeResponse,
    GitHubImportItem,
    GitHubImportRequest,
    GitHubImportResponse,
    GitHubRepoResponse,
    GitHubStatusResponse,
    NotionAuthorizeResponse,
    NotionImportItem,
    NotionImportRequest,
    NotionImportResponse,
    NotionPageResponse,
    NotionStatusResponse,
)
from app.services.github import (
    GitHubAPIError,
    GitHubClient,
    GitHubConfigurationError,
    GitHubIntegrationService,
    GitHubNotConnected,
)
from app.services.github import (
    build_authorize_url as build_github_authorize_url,
)
from app.services.github import (
    create_oauth_state as create_github_oauth_state,
)
from app.services.github import (
    exchange_code_for_token as exchange_github_code_for_token,
)
from app.services.github import (
    parse_oauth_state as parse_github_oauth_state,
)
from app.services.knowledge import KnowledgeService
from app.services.notion import (
    NotionAPIError,
    NotionClient,
    NotionConfigurationError,
    NotionIntegrationService,
    NotionNotConnected,
)
from app.services.notion import (
    build_authorize_url as build_notion_authorize_url,
)
from app.services.notion import (
    create_oauth_state as create_notion_oauth_state,
)
from app.services.notion import (
    exchange_code_for_token as exchange_notion_code_for_token,
)
from app.services.notion import (
    parse_oauth_state as parse_notion_oauth_state,
)
from app.services.projects import ProjectService, SpaceNotFound
from app.services.queue import JobQueue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_notion_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotionIntegrationService:
    return NotionIntegrationService(session)


def get_github_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GitHubIntegrationService:
    return GitHubIntegrationService(session)


def get_knowledge_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeService:
    return KnowledgeService(session, queue=JobQueue())


@router.get("/notion/authorize", response_model=NotionAuthorizeResponse)
async def notion_authorize(
    workspace_id: Annotated[UUID, Query()],
    space_id: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> NotionAuthorizeResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    projects = ProjectService(session)
    try:
        await projects.require_space(space_id=space_id, workspace_id=workspace_id)
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        state = create_notion_oauth_state(
            user_id=user.id,
            workspace_id=workspace_id,
            space_id=space_id,
        )
        url = build_notion_authorize_url(state=state)
    except NotionConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return NotionAuthorizeResponse(authorize_url=url)


@router.get("/notion/callback")
async def notion_callback(
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    _session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RedirectResponse:
    frontend = settings.frontend_origin.rstrip("/")
    try:
        claims = parse_notion_oauth_state(state)
        token_payload = await exchange_notion_code_for_token(code)
        access_token = str(token_payload["access_token"])
        await service.upsert_connection(
            user_id=claims.user_id,
            workspace_id=claims.workspace_id,
            access_token=access_token,
            external_workspace_id=str(token_payload.get("workspace_id") or "")
            or None,
            external_workspace_name=str(token_payload.get("workspace_name") or "")
            or None,
        )
    except (ValueError, NotionConfigurationError, NotionAPIError) as exc:
        logger.exception("Notion OAuth callback failed")
        return RedirectResponse(
            url=f"{frontend}/?notion=error&detail={type(exc).__name__}",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        url=f"{frontend}/?notion=connected",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/notion/status", response_model=NotionStatusResponse)
async def notion_status(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> NotionStatusResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    connection = await service.get_connection(
        user_id=user.id, workspace_id=workspace_id
    )
    if connection is None:
        return NotionStatusResponse(connected=False)
    return NotionStatusResponse(
        connected=True,
        workspace_name=connection.external_workspace_name,
        workspace_id=connection.external_workspace_id,
    )


@router.delete("/notion", status_code=status.HTTP_204_NO_CONTENT)
async def notion_disconnect(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        await service.disconnect(user_id=user.id, workspace_id=workspace_id)
    except NotionNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/notion/pages", response_model=list[NotionPageResponse])
async def notion_pages(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[NotionPageResponse]:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        token = await service.access_token(user_id=user.id, workspace_id=workspace_id)
    except NotionNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        async with NotionClient(token) as client:
            pages = await client.search_pages()
    except NotionAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [NotionPageResponse(id=page.id, title=page.title) for page in pages]


@router.post(
    "/notion/import",
    response_model=NotionImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def notion_import(
    payload: NotionImportRequest,
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    knowledge: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> NotionImportResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    projects = ProjectService(session)
    try:
        await projects.require_space(
            space_id=payload.space_id, workspace_id=payload.workspace_id
        )
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        token = await service.access_token(
            user_id=user.id, workspace_id=payload.workspace_id
        )
    except NotionNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    items: list[NotionImportItem] = []
    try:
        async with NotionClient(token) as client:
            for page_id in payload.page_ids:
                try:
                    filename, markdown = await client.export_page_markdown(page_id)
                    document = await knowledge.enqueue(
                        workspace_id=payload.workspace_id,
                        space_id=payload.space_id,
                        filename=filename,
                        content_type="text/markdown",
                        data=markdown.encode("utf-8"),
                    )
                    items.append(
                        NotionImportItem(
                            page_id=page_id,
                            document_id=document.id,
                            filename=filename,
                            status="pending",
                        )
                    )
                except Exception as exc:
                    logger.exception("Failed to import Notion page %s", page_id)
                    items.append(
                        NotionImportItem(
                            page_id=page_id,
                            status="failed",
                            error=f"{type(exc).__name__}: import failed",
                        )
                    )
    except NotionAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return NotionImportResponse(items=items)


@router.get("/github/authorize", response_model=GitHubAuthorizeResponse)
async def github_authorize(
    workspace_id: Annotated[UUID, Query()],
    space_id: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> GitHubAuthorizeResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    projects = ProjectService(session)
    try:
        await projects.require_space(space_id=space_id, workspace_id=workspace_id)
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        state = create_github_oauth_state(
            user_id=user.id,
            workspace_id=workspace_id,
            space_id=space_id,
        )
        url = build_github_authorize_url(state=state)
    except GitHubConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GitHubAuthorizeResponse(authorize_url=url)


@router.get("/github/callback")
async def github_callback(
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    service: Annotated[GitHubIntegrationService, Depends(get_github_service)],
    _session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RedirectResponse:
    frontend = settings.frontend_origin.rstrip("/")
    try:
        claims = parse_github_oauth_state(state)
        token_payload = await exchange_github_code_for_token(code)
        access_token = str(token_payload["access_token"])
        async with GitHubClient(access_token) as client:
            user_payload = await client.get_user()
        await service.upsert_connection(
            user_id=claims.user_id,
            workspace_id=claims.workspace_id,
            access_token=access_token,
            external_workspace_id=str(user_payload.get("id") or "") or None,
            external_workspace_name=str(user_payload.get("login") or "") or None,
        )
    except (ValueError, GitHubConfigurationError, GitHubAPIError) as exc:
        logger.exception("GitHub OAuth callback failed")
        return RedirectResponse(
            url=f"{frontend}/?github=error&detail={type(exc).__name__}",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        url=f"{frontend}/?github=connected",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/github/status", response_model=GitHubStatusResponse)
async def github_status(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[GitHubIntegrationService, Depends(get_github_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> GitHubStatusResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    connection = await service.get_connection(
        user_id=user.id, workspace_id=workspace_id
    )
    if connection is None:
        return GitHubStatusResponse(connected=False)
    return GitHubStatusResponse(
        connected=True,
        login=connection.external_workspace_name,
        user_id=connection.external_workspace_id,
    )


@router.delete("/github", status_code=status.HTTP_204_NO_CONTENT)
async def github_disconnect(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[GitHubIntegrationService, Depends(get_github_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        await service.disconnect(user_id=user.id, workspace_id=workspace_id)
    except GitHubNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/github/repos", response_model=list[GitHubRepoResponse])
async def github_repos(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[GitHubIntegrationService, Depends(get_github_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[GitHubRepoResponse]:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        token = await service.access_token(user_id=user.id, workspace_id=workspace_id)
    except GitHubNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        async with GitHubClient(token) as client:
            repos = await client.list_repos()
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [
        GitHubRepoResponse(
            id=repo.id,
            full_name=repo.full_name,
            private=repo.private,
            default_branch=repo.default_branch,
        )
        for repo in repos
    ]


@router.post(
    "/github/import",
    response_model=GitHubImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def github_import(
    payload: GitHubImportRequest,
    service: Annotated[GitHubIntegrationService, Depends(get_github_service)],
    knowledge: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> GitHubImportResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    projects = ProjectService(session)
    try:
        await projects.require_space(
            space_id=payload.space_id, workspace_id=payload.workspace_id
        )
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        token = await service.access_token(
            user_id=user.id, workspace_id=payload.workspace_id
        )
    except GitHubNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    items: list[GitHubImportItem] = []
    try:
        async with GitHubClient(token) as client:
            for full_name in payload.repo_full_names:
                try:
                    files = await client.export_repo_markdown(full_name)
                    if not files:
                        items.append(
                            GitHubImportItem(
                                repo_full_name=full_name,
                                status="failed",
                                error="No markdown files found",
                            )
                        )
                        continue
                    for file in files:
                        try:
                            document = await knowledge.enqueue(
                                workspace_id=payload.workspace_id,
                                space_id=payload.space_id,
                                filename=file.filename,
                                content_type="text/markdown",
                                data=file.content.encode("utf-8"),
                            )
                            items.append(
                                GitHubImportItem(
                                    repo_full_name=full_name,
                                    path=file.path,
                                    document_id=document.id,
                                    filename=file.filename,
                                    status="pending",
                                )
                            )
                        except Exception:
                            logger.exception(
                                "Failed to enqueue GitHub file %s:%s",
                                full_name,
                                file.path,
                            )
                            items.append(
                                GitHubImportItem(
                                    repo_full_name=full_name,
                                    path=file.path,
                                    status="failed",
                                    error="enqueue failed",
                                )
                            )
                except Exception as exc:
                    logger.exception("Failed to import GitHub repo %s", full_name)
                    items.append(
                        GitHubImportItem(
                            repo_full_name=full_name,
                            status="failed",
                            error=f"{type(exc).__name__}: import failed",
                        )
                    )
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return GitHubImportResponse(items=items)
