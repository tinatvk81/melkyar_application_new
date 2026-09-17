from alembic import op
import sqlalchemy as sa

revision = "b0c1d2e3f4a5"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column("deals", "deal_amount",
                    type_=sa.BigInteger(), postgresql_using="deal_amount::bigint")
    op.alter_column("deals", "commission_amount",
                    type_=sa.BigInteger(), postgresql_using="commission_amount::bigint")
    op.alter_column("commission_payments", "amount",
                    type_=sa.BigInteger(), postgresql_using="amount::bigint")

def downgrade():
    op.alter_column("deals", "deal_amount",
                    type_=sa.Integer(), postgresql_using="deal_amount::int")
    op.alter_column("deals", "commission_amount",
                    type_=sa.Integer(), postgresql_using="commission_amount::int")
    op.alter_column("commission_payments", "amount",
                    type_=sa.Integer(), postgresql_using="amount::int")