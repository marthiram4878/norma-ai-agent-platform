"""Integration API contracts."""

from uuid import UUID

from pydantic import BaseModel, Field


class NotionAuthorizeResponse(BaseModel):
    authorize_url: str


class NotionStatusResponse(BaseModel):
    connected: bool
    workspace_name: str | None = None
    workspace_id: str | None = None


class NotionPageResponse(BaseModel):
    id: str
    title: str


class NotionImportRequest(BaseModel):
    workspace_id: UUID
    space_id: UUID
    page_ids: list[str] = Field(min_length=1, max_length=25)


class NotionImportItem(BaseModel):
    page_id: str
    document_id: UUID | None = None
    filename: str | None = None
    status: str
    error: str | None = None


class NotionImportResponse(BaseModel):
    items: list[NotionImportItem]


class GitHubAuthorizeResponse(BaseModel):
    authorize_url: str


class GitHubStatusResponse(BaseModel):
    connected: bool
    login: str | None = None
    user_id: str | None = None


class GitHubRepoResponse(BaseModel):
    id: int
    full_name: str
    private: bool
    default_branch: str


class GitHubImportRequest(BaseModel):
    workspace_id: UUID
    space_id: UUID
    repo_full_names: list[str] = Field(min_length=1, max_length=10)


class GitHubImportItem(BaseModel):
    repo_full_name: str
    path: str | None = None
    document_id: UUID | None = None
    filename: str | None = None
    status: str
    error: str | None = None


class GitHubImportResponse(BaseModel):
    items: list[GitHubImportItem]
