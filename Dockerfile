# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add metadata
LABEL org.opencontainers.image.title="Hassaniya Arabic Normalizer" \
      org.opencontainers.image.description="A robust normalizer for Hassaniya Arabic text" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="Hassaniya Normalizer Contributors" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/yourusername/hassaniya-normalizer"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY server.py .
COPY README.md .
COPY LICENSE .

# Install Python dependencies and build package
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir build && \
    python -m build && \
    pip install --no-cache-dir dist/*.whl

# Production stage
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r hassy && useradd -r -g hassy hassy

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy installed package from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/hassy-* /usr/local/bin/
COPY --from=builder /app/server.py /app/

# Create directories and set permissions
RUN mkdir -p /app/logs && \
    chown -R hassy:hassy /app

# Switch to non-root user
USER hassy

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    FLASK_DEBUG=0

# Expose port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/healthz || exit 1

# Default command
CMD ["hassy-web"]

# Alternative commands for different use cases:
# For CLI usage: docker run --rm -i hassy-normalizer hassy-normalize --help
# For custom port: docker run -p 5000:5000 -e PORT=5000 hassy-normalizer
# For debug mode: docker run -p 8000:8000 -e FLASK_DEBUG=1 hassy-normalizer

# Build instructions:
# docker build -t hassy-normalizer .
# docker build -t hassy-normalizer:latest --build-arg VERSION=0.1.0 .
# docker build -t hassy-normalizer:0.1.0 --build-arg VERSION=0.1.0 --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') --build-arg VCS_REF=$(git rev-parse HEAD) .

# Run instructions:
# docker run -p 8000:8000 hassy-normalizer
# docker run -p 8000:8000 -e PORT=8000 -e FLASK_DEBUG=0 hassy-normalizer
# docker run --rm -i hassy-normalizer hassy-normalize --help
# echo "قال الرجل" | docker run --rm -i hassy-normalizer hassy-normalize --diff