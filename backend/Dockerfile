FROM python:3.11-slim

# Font Liberation: usati da services/og.py per le immagini OG.
RUN apt-get update && apt-get install -y --no-install-recommends fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
CMD uvicorn server:app --host 0.0.0.0 --port $PORT
