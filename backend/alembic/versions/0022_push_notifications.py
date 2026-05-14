"""Add push_subscriptions, notification_prefs and notification_log tables

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("endpoint", sa.Text, nullable=False, unique=True),
        sa.Column("p256dh", sa.Text, nullable=False),
        sa.Column("auth", sa.Text, nullable=False),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

    op.create_table(
        "notification_prefs",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("quiet_start", sa.Integer, nullable=False, server_default="22"),
        sa.Column("quiet_end", sa.Integer, nullable=False, server_default="8"),
        # Meal reminders
        sa.Column("breakfast_on", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("breakfast_time", sa.String(5), nullable=False, server_default="08:30"),
        sa.Column("lunch_on", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("lunch_time", sa.String(5), nullable=False, server_default="13:30"),
        sa.Column("dinner_on", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("dinner_time", sa.String(5), nullable=False, server_default="21:00"),
        # Streak alert
        sa.Column("streak_on", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("streak_time", sa.String(5), nullable=False, server_default="20:00"),
        sa.Column("streak_min_days", sa.Integer, nullable=False, server_default="3"),
        # Daily summary
        sa.Column("summary_on", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("summary_time", sa.String(5), nullable=False, server_default="21:30"),
        # Water reminder
        sa.Column("water_on", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("water_time", sa.String(5), nullable=False, server_default="16:00"),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("notif_type", sa.String(50), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notification_log_user_id", "notification_log", ["user_id"])


def downgrade() -> None:
    op.drop_table("notification_log")
    op.drop_table("notification_prefs")
    op.drop_table("push_subscriptions")
