# Production-ready multi-stage Docker build
# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_ENV=production
ARG VERSION=1.0.0

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /build

# Copy requirements and install Python dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --user --no-warn-script-location -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim as production

# Set metadata labels
LABEL maintainer="AI Recommendation Service" \
      version="${VERSION}" \
      description="Production-ready AI-powered recommendation API"

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    PYTHONPATH=/app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directory with proper permissions
RUN mkdir -p /app /app/logs /app/data /app/ml_models \
    && chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser ./app /app/app
COPY --chown=appuser:appuser ./ml_models /app/ml_models
COPY --chown=appuser:appuser ./data /app/data

# Copy configuration files
COPY --chown=appuser:appuser ./.env.example /app/.env.example
COPY --chown=appuser:appuser ./docker-entrypoint.sh /app/docker-entrypoint.sh

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Add local bin to PATH for user-installed packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint script for graceful startup
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
