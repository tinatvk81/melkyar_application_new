from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "b7c2d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("properties", sa.Column("expire_notified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("properties", sa.Column("expire_review_at", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("properties", "expire_review_at")
    op.drop_column("properties", "expire_notified_at")