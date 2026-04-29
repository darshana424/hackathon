# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create data directory for persistent storage (optional if on free tier)
RUN mkdir -p /data && chmod 777 /data

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

COPY --from=builder /root/.local /root/.local
COPY . .

# Install system dependencies for Playwright & browsers
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && playwright install-deps chromium \
    && playwright install chromium \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

# Use gunicorn with 1 worker to stay within Free Tier memory limits (512MB)
CMD ["gunicorn", "app:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "300"]
