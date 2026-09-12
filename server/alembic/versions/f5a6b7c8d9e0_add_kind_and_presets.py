from alembic import op
import sqlalchemy as sa

revision = "f5a6b7c8d9e0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("commission_payments",
                  sa.Column("kind", sa.String(length=16), nullable=False, server_default="to_agent"))
    op.create_table(
        "filter_presets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("filter_presets")
    op.drop_column("commission_payments", "kind")