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

EXPOSE 8000

# MPLBACKEND=Agg is critical — prevents matplotlib from attempting
# to connect to a display server (which doesn't exist in a container)
ENV MPLBACKEND=Agg
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
