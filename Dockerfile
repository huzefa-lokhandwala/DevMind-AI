# Use official Python 3.12 slim base image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 \
    EMBEDDING_THREADS=1 \
    EMBEDDING_BATCH_SIZE=1

WORKDIR /app

# Install essential system build tools and git for repository cloning support
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies with extended network timeout
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Copy application source code
COPY . .

# Ensure entrypoint script is executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose FastAPI application port
EXPOSE 8000

# Set entrypoint script to execute migrations and start Uvicorn
ENTRYPOINT ["/app/docker-entrypoint.sh"]
