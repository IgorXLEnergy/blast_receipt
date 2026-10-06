FROM python:3.11-slim

ARG PADDLE_INDEX_URL=https://www.paddlepaddle.org.cn/packages/stable/cpu/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip \
    && python -m pip install "paddlepaddle>=3.2,<4" -i ${PADDLE_INDEX_URL}

WORKDIR /app
COPY service/requirements.txt ./requirements.txt
RUN python -m pip install -r requirements.txt

COPY service/app ./app
COPY service/static ./static
COPY shared /shared

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
