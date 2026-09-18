FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# PyPI مستقیم از این شبکه در دسترس نیست — آینهٔ تست‌شده استفاده می‌شود
RUN pip install --no-cache-dir \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    --timeout 120 --retries 10 \
    -r requirements.txt

COPY . .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]