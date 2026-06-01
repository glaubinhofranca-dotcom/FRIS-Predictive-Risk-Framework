FROM python:3.11-slim

WORKDIR /app

# System dependencies for matplotlib font rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create sessions directory (will be volume-mounted at runtime)
RUN mkdir -p /app/data/sessions

# Port 7860 is the Hugging Face Spaces default.
# Override via PORT env variable for other platforms (Render, Railway, Fly.io).
# docker-compose sets PORT=8000 for local development.
ENV PORT=7860
EXPOSE 7860

# MPLBACKEND=Agg is critical — prevents matplotlib from attempting
# to connect to a display server (which doesn't exist in a container)
ENV MPLBACKEND=Agg
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
