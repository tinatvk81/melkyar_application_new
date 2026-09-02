from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

DATABASE_URL = (
    f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

# نکته‌ی امنیتی: POSTGRES_HOST باید "localhost" بماند — یعنی پستگرس فقط از خودِ
# همین سرور در دسترس است. کلاینت‌های روی شبکه هرگز مستقیم به پستگرس وصل نمی‌شوند؛
# آن‌ها فقط با FastAPI (این برنامه) روی پورت ۸۰۰۰ صحبت می‌کنند.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
