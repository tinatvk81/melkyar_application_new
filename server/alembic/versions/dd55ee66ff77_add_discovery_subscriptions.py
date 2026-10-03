"""اشتراک/فیلترهای ملک‌یاب برای هر کاربر + ایندکس‌های discovery

Revision ID: dd55ee66ff77
Revises: cc33dd44ee55
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "dd55ee66ff77"
down_revision = "cc33dd44ee55"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "discovery_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("allowed_districts", postgresql.JSONB(), nullable=True),
        sa.Column("blocked_districts", postgresql.JSONB(), nullable=True),
        sa.Column("deal_types", postgresql.JSONB(), nullable=True),
        sa.Column("show_unknown", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade():
    op.drop_table("discovery_subscriptions")