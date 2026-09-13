from alembic import op
import sqlalchemy as sa

revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "bot_faq",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
    )

def downgrade():
    op.drop_table("bot_faq")