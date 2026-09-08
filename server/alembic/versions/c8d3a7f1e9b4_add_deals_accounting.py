from alembic import op
import sqlalchemy as sa

revision = "c8d3a7f1e9b4"
down_revision = "f4a9c1e2d7b3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("commission_rates", sa.JSON(), nullable=True))
    op.execute("ALTER TYPE propertystatus ADD VALUE IF NOT EXISTS 'sold'")

    op.create_table(
        "deals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("deal_amount", sa.Integer(), nullable=False),
        sa.Column("commission_percent", sa.Float(), nullable=False),
        sa.Column("commission_amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "finalized", "canceled", name="dealstatus"),
                  nullable=False, server_default="pending"),
        sa.Column("contract_date", sa.Date(), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "commission_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id"), nullable=False, index=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("receipt_path", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("commission_payments")
    op.drop_table("deals")
    op.drop_column("users", "commission_rates")