# DART-Planner: Production-Ready Autonomous Drone Navigation
# Multi-stage Dockerfile for secure production deployment

# Build stage
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# Install DART-Planner in development mode
RUN pip install --user -e .

# Production stage
FROM python:3.10-slim as production

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r dartplanner && useradd -r -g dartplanner dartplanner

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/dartplanner/.local

# Copy source code
COPY --from=builder /app/src/ ./src/
COPY --from=builder /app/scripts/ ./scripts/
COPY --from=builder /app/pyproject.toml .

# Create web demo directory
RUN mkdir -p /app/web_demo

# Copy web demo files
COPY demos/web_demo/ ./web_demo/

# Set proper ownership
RUN chown -R dartplanner:dartplanner /app

# Switch to non-root user
USER dartplanner

# Add user's local bin to PATH
ENV PATH=/home/dartplanner/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV DART_PLANNER_MODE=production

# Expose port for web interface
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - run the web demo
CMD ["python", "web_demo/app.py"]
