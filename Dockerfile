FROM python:3.13.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "updater.py"]

LABEL org.opencontainers.image.title="Watchless" \
      org.opencontainers.image.version="1.0-beta" \
      org.opencontainers.image.source="https://github.com/fish906/watchless"