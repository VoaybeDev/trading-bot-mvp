# ─── Dockerfile — NexTrade backend pour Hugging Face Spaces ────────────────
# HF Spaces impose :
#   - Port 7860
#   - Utilisateur non-root (uid 1000)
#   - Stockage persistant monté sur /data

FROM python:3.12-slim

LABEL maintainer="VoaybeDev"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /data = volume persistant HF Spaces pour SQLite
RUN mkdir -p /data

# Utilisateur non-root requis par HF Spaces
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /data

USER appuser

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]