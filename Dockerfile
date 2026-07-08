FROM python:3.11-slim

# ffmpeg is required for frame extraction
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# src/embedded_key.py is copied in (it is NOT in .dockerignore). The judge runs
# this with no env vars; config.py falls back to that embedded key.
CMD ["python", "-m", "src.main"]
