from alembic import op
import sqlalchemy as sa

revision = "e9f1a2b3c4d5"
down_revision = "c8d3a7f1e9b4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "client_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_agent_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("customer_name", sa.String(length=128), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("deal_type", sa.String(length=16), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("district", sa.String(length=64), nullable=True),
        sa.Column("min_area", sa.Float(), nullable=True),
        sa.Column("max_area", sa.Float(), nullable=True),
        sa.Column("min_rooms", sa.Integer(), nullable=True),
        sa.Column("max_price", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("open", "closed", name="requeststatus"),
                  nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("client_requests")