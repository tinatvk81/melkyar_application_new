from alembic import op
import sqlalchemy as sa

revision = "a9b0c1d2e3f4"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("properties", sa.Column("property_types", sa.JSON(), nullable=True))

def downgrade():
    op.drop_column("properties", "property_types")