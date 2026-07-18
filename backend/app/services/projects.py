"""Project and knowledge-space application service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.project_models import KnowledgeSpace, Project


class ProjectNotFound(LookupError):
    pass


class SpaceNotFound(LookupError):
    pass


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_defaults(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Project:
        existing = await self.session.scalar(
            select(Project)
            .options(selectinload(Project.spaces))
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.created_at.asc())
        )
        if existing is not None:
            if not existing.spaces:
                space = KnowledgeSpace(project_id=existing.id, name="Main")
                self.session.add(space)
                await self.session.flush()
                await self.session.refresh(existing, attribute_names=["spaces"])
            return existing

        project = Project(
            workspace_id=workspace_id,
            name="My project",
            created_by=user_id,
        )
        self.session.add(project)
        await self.session.flush()
        self.session.add(KnowledgeSpace(project_id=project.id, name="Main"))
        await self.session.flush()
        await self.session.refresh(project, attribute_names=["spaces"])
        return project

    async def list_projects(self, *, workspace_id: UUID) -> list[Project]:
        rows = (
            await self.session.scalars(
                select(Project)
                .options(selectinload(Project.spaces))
                .where(Project.workspace_id == workspace_id)
                .order_by(Project.created_at.asc())
            )
        ).all()
        return list(rows)

    async def create_project(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        name: str,
        space_name: str = "Main",
    ) -> Project:
        project = Project(
            workspace_id=workspace_id,
            name=name.strip(),
            created_by=user_id,
        )
        self.session.add(project)
        await self.session.flush()
        self.session.add(
            KnowledgeSpace(project_id=project.id, name=space_name.strip() or "Main")
        )
        await self.session.flush()
        await self.session.refresh(project, attribute_names=["spaces"])
        return project

    async def create_space(
        self,
        *,
        project_id: UUID,
        workspace_id: UUID,
        name: str,
    ) -> KnowledgeSpace:
        project = await self.session.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        if project is None:
            raise ProjectNotFound("Project not found")
        space = KnowledgeSpace(project_id=project.id, name=name.strip())
        self.session.add(space)
        await self.session.flush()
        await self.session.refresh(space)
        return space

    async def require_space(
        self,
        *,
        space_id: UUID,
        workspace_id: UUID,
    ) -> KnowledgeSpace:
        space = await self.session.scalar(
            select(KnowledgeSpace)
            .join(Project)
            .where(
                KnowledgeSpace.id == space_id,
                Project.workspace_id == workspace_id,
            )
        )
        if space is None:
            raise SpaceNotFound("Knowledge space not found")
        return space

    async def default_space_id(self, *, workspace_id: UUID, user_id: UUID) -> UUID:
        project = await self.ensure_defaults(
            workspace_id=workspace_id, user_id=user_id
        )
        return project.spaces[0].id
