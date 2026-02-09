FROM python:3.12.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Seoul 

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 libstdc++6 tzdata \
 && rm -rf /var/lib/apt/lists/*

# 있으면 사용
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

CMD ["python", "get_extra_data_runner.py"]