from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("follow_ups", sa.Column("due_time", sa.String(length=5), nullable=True))

def downgrade():
    op.drop_column("follow_ups", "due_time")