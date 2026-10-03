"""ایندکس‌های discovery برای سرعت لیست/فیلتر

Revision ID: cc33dd44ee55
Revises: bb22cc33dd44
"""
from alembic import op

revision = "cc33dd44ee55"
down_revision = "bb22cc33dd44"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_discovery_listings_posted_at", "discovery_listings", ["posted_at"])
    op.create_index("ix_discovery_listings_neighborhood", "discovery_listings", ["neighborhood_id"])
    op.create_index("ix_discovery_listings_converted", "discovery_listings", ["converted_property_id"])
    op.create_index("ix_discovery_listings_dismissed", "discovery_listings", ["dismissed_at"])


def downgrade():
    for name in ("ix_discovery_listings_dismissed", "ix_discovery_listings_converted",
                 "ix_discovery_listings_neighborhood", "ix_discovery_listings_posted_at"):
        op.drop_index(name, table_name="discovery_listings")