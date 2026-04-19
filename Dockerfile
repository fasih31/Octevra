# ============================================================
# Orkavia AI-OS Nexus — Dockerfile
# © 2026 Fasih ur Rehman. All Rights Reserved.
# ============================================================
FROM python:3.11-slim

LABEL maintainer="Fasih ur Rehman"
LABEL org.opencontainers.image.title="Orkavia AI-OS Nexus"
LABEL org.opencontainers.image.description="Orkavia AI-OS Nexus — Dual-mode AI Operating System"
LABEL org.opencontainers.image.vendor="Fasih ur Rehman"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.licenses="Proprietary"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    NEXUS_MASTER_SECRET="nexus-change-this-secret-in-production"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create data directory
RUN mkdir -p data

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/health')"

# Start the server
CMD ["uvicorn", "ai_os_nexus.api.main_api:app", "--host", "0.0.0.0", "--port", "8000"]
