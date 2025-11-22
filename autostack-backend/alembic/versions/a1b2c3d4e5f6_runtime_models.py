"""runtime models

Revision ID: a1b2c3d4e5f6
Revises: 7922132ebbdd
Create Date: 2025-11-21 20:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7922132ebbdd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("runtime", sa.String(length=50), nullable=False, server_default="static"),
    )
    op.alter_column("projects", "runtime", server_default=None)

    op.create_table(
        "deployment_containers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deployment_id", sa.UUID(), nullable=False),
        sa.Column("container_id", sa.String(length=255), nullable=False),
        sa.Column("image", sa.String(length=255), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("stopped_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deployment_containers_deployment_id",
        "deployment_containers",
        ["deployment_id"],
        unique=False,
    )

    op.create_table(
        "deployment_health_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deployment_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("is_live", sa.Boolean(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deployment_health_checks_deployment_id",
        "deployment_health_checks",
        ["deployment_id"],
        unique=False,
    )

    op.create_table(
        "deployment_runtime_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deployment_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("log_level", sa.String(length=20), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deployment_runtime_logs_deployment_id",
        "deployment_runtime_logs",
        ["deployment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_deployment_runtime_logs_deployment_id", table_name="deployment_runtime_logs")
    op.drop_table("deployment_runtime_logs")

    op.drop_index("ix_deployment_health_checks_deployment_id", table_name="deployment_health_checks")
    op.drop_table("deployment_health_checks")

    op.drop_index("ix_deployment_containers_deployment_id", table_name="deployment_containers")
    op.drop_table("deployment_containers")

    op.drop_column("projects", "runtime")
