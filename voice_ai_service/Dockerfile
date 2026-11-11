FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/app/src

EXPOSE 8000 50051

CMD ["sh", "-c", "alembic -c src/voice_ai_service/app/alembic.ini upgrade head && exec uvicorn voice_ai_service.main:app --host 0.0.0.0 --port 8000"]
