# DART-Planner: Production-Ready Autonomous Drone Navigation
# Docker container for easy demonstration and development

FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# Install DART-Planner in development mode
RUN pip install -e .

# Create web demo directory
RUN mkdir -p /app/web_demo

# Copy web demo files
COPY demos/web_demo/ ./web_demo/

# Expose port for web interface
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV DART_PLANNER_MODE=demo

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - run the web demo
CMD ["python", "web_demo/app.py"] 