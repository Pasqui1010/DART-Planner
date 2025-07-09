# DART-Planner: Production-Ready Autonomous Drone Navigation
# Multi-stage Dockerfile with proper dependency management

# Base stage with common dependencies
FROM python:3.11-slim as base

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r dartplanner && useradd -r -g dartplanner dartplanner

# Set working directory
WORKDIR /app

# Dependencies stage - cache Python dependencies separately
FROM base as deps

# Install build dependencies only for this stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy lockfiles for better caching
COPY requirements/requirements.txt ./requirements/requirements.txt

# Install Python dependencies using lockfile
RUN pip install --no-cache-dir --user --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user numpy msgpack-rpc-python && \
    pip install --no-cache-dir --user -r requirements/requirements.txt

# Build stage - install the package
FROM deps as builder

# Copy package files
COPY pyproject.toml ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install DART-Planner in production mode
RUN pip install --user --no-deps -e .

# Production stage - minimal runtime image
FROM base as production

# Copy Python packages from builder
COPY --from=builder /root/.local /home/dartplanner/.local

# Copy only necessary source code
COPY --from=builder /app/src/ ./src/
COPY --from=builder /app/scripts/ ./scripts/
COPY pyproject.toml ./

# Copy web demo files
COPY demos/web_demo/ ./web_demo/

# Copy configuration files
COPY config/ ./config/

# Create necessary directories and set ownership
RUN mkdir -p /home/dartplanner/.dart_planner && \
    mkdir -p /home/dartplanner/.config && \
    chown -R dartplanner:dartplanner /app && \
    chown -R dartplanner:dartplanner /home/dartplanner

# Switch to non-root user
USER dartplanner

# Environment setup
ENV PATH=/home/dartplanner/.local/bin:$PATH \
    PYTHONPATH=/app \
    DART_PLANNER_MODE=production \
    PYTHONUNBUFFERED=1 \
    DART_SECRET_KEY=dev-secret-key-for-docker-testing \
    DART_ZMQ_SECRET=dev-zmq-secret-for-docker-testing \
    MPLCONFIGDIR=/home/dartplanner/.config/matplotlib

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["python", "web_demo/app.py"]
