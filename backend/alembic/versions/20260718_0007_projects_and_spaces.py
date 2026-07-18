"""Create projects, knowledge spaces, and space-scoped foreign keys."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260718_0007"
down_revision: str | None = "20260718_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"])
    op.create_table(
        "knowledge_spaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_spaces_project_id", "knowledge_spaces", ["project_id"]
    )

    for table in (
        "documents",
        "document_chunks",
        "workflow_runs",
        "conversations",
        "workspace_memories",
    ):
        op.add_column(table, sa.Column("space_id", sa.Uuid(), nullable=True))

    # Backfill: one default project + Main space per workspace that has members.
    conn = op.get_bind()
    workspaces = conn.execute(
        sa.text(
            """
            SELECT w.id AS workspace_id, m.user_id AS owner_id
            FROM workspaces w
            JOIN workspace_memberships m ON m.workspace_id = w.id
            WHERE m.role = 'owner'
            """
        )
    ).mappings().all()
    for row in workspaces:
        project_id = conn.execute(
            sa.text(
                """
                INSERT INTO projects (id, workspace_id, name, created_by)
                VALUES (gen_random_uuid(), :workspace_id, 'My project', :owner_id)
                RETURNING id
                """
            ),
            {"workspace_id": row["workspace_id"], "owner_id": row["owner_id"]},
        ).scalar_one()
        space_id = conn.execute(
            sa.text(
                """
                INSERT INTO knowledge_spaces (id, project_id, name)
                VALUES (gen_random_uuid(), :project_id, 'Main')
                RETURNING id
                """
            ),
            {"project_id": project_id},
        ).scalar_one()
        for table in (
            "documents",
            "document_chunks",
            "workflow_runs",
            "conversations",
            "workspace_memories",
        ):
            conn.execute(
                sa.text(
                    f"""
                    UPDATE {table}
                    SET space_id = :space_id
                    WHERE workspace_id = :workspace_id AND space_id IS NULL
                    """
                ),
                {"space_id": space_id, "workspace_id": row["workspace_id"]},
            )

    for table in (
        "documents",
        "document_chunks",
        "workflow_runs",
        "conversations",
        "workspace_memories",
    ):
        op.alter_column(
            table,
            "space_id",
            existing_type=postgresql.UUID(),
            nullable=False,
        )
        op.create_index(f"ix_{table}_space_id", table, ["space_id"])
        op.create_foreign_key(
            f"fk_{table}_space_id",
            table,
            "knowledge_spaces",
            ["space_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table in (
        "workspace_memories",
        "conversations",
        "workflow_runs",
        "document_chunks",
        "documents",
    ):
        op.drop_constraint(f"fk_{table}_space_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_space_id", table_name=table)
        op.drop_column(table, "space_id")
    op.drop_index("ix_knowledge_spaces_project_id", table_name="knowledge_spaces")
    op.drop_table("knowledge_spaces")
    op.drop_index("ix_projects_workspace_id", table_name="projects")
    op.drop_table("projects")
