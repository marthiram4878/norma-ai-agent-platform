"""Project and knowledge-space API contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeSpaceResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    created_at: datetime


class ProjectResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    spaces: list[KnowledgeSpaceResponse]
    created_at: datetime


class ProjectCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=120)


class SpaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
