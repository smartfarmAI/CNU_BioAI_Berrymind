FROM python:3.12.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Seoul \
    ACTION_IO_HOST=http://actionio:8000

WORKDIR /app

# 있으면 사용
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
EXPOSE 9000

# FastAPI 엔트리포인트(파일/모듈명 맞게 수정)
CMD ["uvicorn", "fsm_server:app", "--host", "0.0.0.0", "--port", "9000"]
