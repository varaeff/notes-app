"""add telegram reminder time

Revision ID: a0f4c3d2e9b1
Revises: 63d8d6629c31
Create Date: 2026-07-22 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a0f4c3d2e9b1"
down_revision = "63d8d6629c31"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "telegram_settings",
        sa.Column(
            "reminder_time",
            sa.Time(),
            nullable=False,
            server_default="09:00:00",
        ),
    )


def downgrade():
    op.drop_column("telegram_settings", "reminder_time")
