from alembic import op
import sqlalchemy as sa

revision = "b7c2d4e5f6a7"
down_revision = "e9f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "follow_ups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id"), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True, index=True),
        sa.Column("status", sa.Enum("pending", "done", "canceled", name="followupstatus"),
                  nullable=False, server_default="pending"),
        sa.Column("reminded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(length=32), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("notifications")
    op.drop_table("follow_ups")