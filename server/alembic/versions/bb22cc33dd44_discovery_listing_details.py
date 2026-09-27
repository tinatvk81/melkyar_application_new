"""جزئیات آگهی‌های ملک‌یاب: متراژ/اتاق/ودیعه/اجاره + city + dismissed_at

Revision ID: bb22cc33dd44
Revises: 07910d4ca1b0
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "bb22cc33dd44"
down_revision = "07910d4ca1b0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("discovery_listings", sa.Column("city", sa.String(length=50), nullable=True))
    op.add_column("discovery_listings", sa.Column("area_m2", sa.Integer(), nullable=True))
    op.add_column("discovery_listings", sa.Column("rooms", sa.Integer(), nullable=True))
    op.add_column("discovery_listings", sa.Column("deposit", sa.BigInteger(), nullable=True))
    op.add_column("discovery_listings", sa.Column("monthly_rent", sa.BigInteger(), nullable=True))
    op.add_column("discovery_listings", sa.Column("attributes", postgresql.JSONB(), nullable=True))
    op.add_column("discovery_listings", sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    for col in ("dismissed_at", "attributes", "monthly_rent", "deposit", "rooms", "area_m2", "city"):
        op.drop_column("discovery_listings", col)