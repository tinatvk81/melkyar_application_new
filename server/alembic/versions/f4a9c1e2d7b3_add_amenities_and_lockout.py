from alembic import op
import sqlalchemy as sa

revision = "f4a9c1e2d7b3"
down_revision = "816821937b65"   # ← ادامه‌ی زنجیره‌ی موجود، نه ریشه‌ی جدید
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("properties", sa.Column("amenities", sa.JSON(), nullable=True))
    op.add_column("users", sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_attempts")
    op.drop_column("properties", "amenities")