"""ستارهٔ شخصی هر کاربر روی فایل‌ها (علاقه‌مندی per-user)

Revision ID: aa11bb22cc33
Revises: b0c1d2e3f4a5
"""
from alembic import op
import sqlalchemy as sa

revision = "aa11bb22cc33"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "property_id", name="uq_user_property_favorite"),
    )
    op.create_index("ix_property_favorites_user_id", "property_favorites", ["user_id"])
    op.create_index("ix_property_favorites_property_id", "property_favorites", ["property_id"])


def downgrade():
    op.drop_index("ix_property_favorites_property_id", table_name="property_favorites")
    op.drop_index("ix_property_favorites_user_id", table_name="property_favorites")
    op.drop_table("property_favorites")