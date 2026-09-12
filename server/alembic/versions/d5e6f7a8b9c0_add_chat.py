from alembic import op
import sqlalchemy as sa

revision = "d5e6f7a8b9c0"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("receiver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

def downgrade():
    op.drop_table("chat_messages")