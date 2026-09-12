from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("filter_presets", sa.Column("pending_delete", sa.Boolean(),
                                              nullable=False, server_default=sa.text("false")))

def downgrade():
    op.drop_column("filter_presets", "pending_delete")