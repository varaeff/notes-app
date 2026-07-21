"""rename telegram link token to code

Revision ID: 63d8d6629c31
Revises: 4b2b826a1668
Create Date: 2026-07-21 17:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "63d8d6629c31"
down_revision = "4b2b826a1668"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "telegram_settings",
        "link_token",
        new_column_name="link_code",
        existing_type=sa.String(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "telegram_settings",
        "link_token_expires_at",
        new_column_name="link_code_expires_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.execute("UPDATE telegram_settings SET link_code = NULL WHERE link_code IS NOT NULL")
    op.alter_column(
        "telegram_settings",
        "link_code",
        existing_type=sa.String(length=128),
        type_=sa.String(length=6),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "telegram_settings",
        "link_code",
        existing_type=sa.String(length=6),
        type_=sa.String(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "telegram_settings",
        "link_code",
        new_column_name="link_token",
        existing_type=sa.String(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "telegram_settings",
        "link_code_expires_at",
        new_column_name="link_token_expires_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
