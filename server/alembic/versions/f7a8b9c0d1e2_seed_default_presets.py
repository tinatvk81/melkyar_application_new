from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None

DEFAULT_PRESETS = [
    ("همه", "{}"),
    ("فروش", '{"deal_type": "sale"}'),
    ("اجاره", '{"deal_type": "rent"}'),
    ("رهن کامل", '{"deal_type": "mortgage"}'),
    ("پیش‌خرید", '{"deal_type": "presale"}'),
    ("فروش زیر ۲ میلیارد", '{"deal_type": "sale", "max_price": 2000000000}'),
    ("متراژ ۱۰۰+", '{"min_area": 100}'),
    ("آسانسور", '{"has_elevator": true}'),
    ("پارکینگ", '{"has_parking": true}'),
]


def upgrade():
    # حذف همنام‌های تکراری (نگه‌داشتن قدیمی‌ترین) تا constraint ساخته شود
    op.execute("""
        DELETE FROM filter_presets a
        USING filter_presets b
        WHERE a.name = b.name AND a.id > b.id
    """)
    op.create_unique_constraint("uq_filter_presets_name", "filter_presets", ["name"])

    for name, params in DEFAULT_PRESETS:
        op.execute(
            sa.text(
                """
                INSERT INTO filter_presets (name, params, requested_by, approved)
                SELECT :name, CAST(:params AS json), u.id, true
                FROM users u
                WHERE u.role = 'admin'
                ORDER BY u.id ASC
                LIMIT 1
                ON CONFLICT (name) DO NOTHING
                """
            ).bindparams(name=name, params=params)
        )


def downgrade():
    op.drop_constraint("uq_filter_presets_name", "filter_presets", type_="unique")