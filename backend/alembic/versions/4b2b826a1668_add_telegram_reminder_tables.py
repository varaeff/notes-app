"""add telegram reminder tables

Revision ID: 4b2b826a1668
Revises: 0002
Create Date: 2026-07-21 09:50:01.679842
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "4b2b826a1668"
down_revision = "0002"
branch_labels = None
depends_on = None


reminder_delivery_status = postgresql.ENUM(
    "pending",
    "processing",
    "sent",
    "failed",
    "cancelled",
    name="reminder_delivery_status",
    create_type=False,
)


def upgrade():
    reminder_delivery_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "telegram_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default=sa.text("'UTC'"),
            nullable=False,
        ),
        sa.Column("link_token", sa.String(length=128), nullable=True),
        sa.Column(
            "link_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id"),
        sa.UniqueConstraint("link_token"),
    )

    op.create_index(
        op.f("ix_telegram_settings_user_id"),
        "telegram_settings",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "note_reminder_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            reminder_delivery_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["notes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "note_id",
            "scheduled_for",
            name="uq_note_reminder_delivery_note_scheduled_for",
        ),
    )

    op.create_index(
        op.f("ix_note_reminder_deliveries_next_attempt_at"),
        "note_reminder_deliveries",
        ["next_attempt_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_note_reminder_deliveries_note_id"),
        "note_reminder_deliveries",
        ["note_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_note_reminder_deliveries_scheduled_for"),
        "note_reminder_deliveries",
        ["scheduled_for"],
        unique=False,
    )
    op.create_index(
        op.f("ix_note_reminder_deliveries_status"),
        "note_reminder_deliveries",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_note_reminder_deliveries_user_id"),
        "note_reminder_deliveries",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_note_reminder_deliveries_user_id"),
        table_name="note_reminder_deliveries",
    )
    op.drop_index(
        op.f("ix_note_reminder_deliveries_status"),
        table_name="note_reminder_deliveries",
    )
    op.drop_index(
        op.f("ix_note_reminder_deliveries_scheduled_for"),
        table_name="note_reminder_deliveries",
    )
    op.drop_index(
        op.f("ix_note_reminder_deliveries_note_id"),
        table_name="note_reminder_deliveries",
    )
    op.drop_index(
        op.f("ix_note_reminder_deliveries_next_attempt_at"),
        table_name="note_reminder_deliveries",
    )

    op.drop_table("note_reminder_deliveries")

    op.drop_index(
        op.f("ix_telegram_settings_user_id"),
        table_name="telegram_settings",
    )
    op.drop_table("telegram_settings")

    reminder_delivery_status.drop(op.get_bind(), checkfirst=True)