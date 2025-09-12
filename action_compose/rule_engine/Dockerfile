FROM python:3.12.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Seoul \
    DATABASE_URL=postgresql+psycopg://admin:admin123@timescaledb:5432/berrymind \
    SCHEDULER_URL=http://scheduler:8001/submit_schedules

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 앱 소스 복사
COPY . .