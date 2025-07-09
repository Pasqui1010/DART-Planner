# ================================
# DART-Planner: Production Docker Image
# Highly optimized multi-stage build for demo deployment
# ================================

# ================================
# Stage 1: Base Dependencies
# ================================
FROM python:3.11-slim AS base

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenGL and graphics support
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    # Networking and monitoring
    curl \
    wget \
    # Security tools
    ca-certificates \
    gnupg \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user for security
RUN groupadd -r dartplanner && useradd -r -g dartplanner dartplanner \
    && mkdir -p /home/dartplanner \
    && chown -R dartplanner:dartplanner /home/dartplanner

# ================================
# Stage 2: Python Dependencies
# ================================
FROM base AS python-deps

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies in layers for better caching
COPY requirements.txt /tmp/requirements.txt

# Install core dependencies first
RUN pip install --no-cache-dir --user \
    numpy>=1.21.0 \
    scipy>=1.7.0 \
    matplotlib>=3.5.0 \
    pillow>=8.3.0

# Install web framework dependencies
RUN pip install --no-cache-dir --user \
    fastapi>=0.68.0 \
    uvicorn[standard]>=0.15.0 \
    websockets>=10.0 \
    jinja2>=3.0.0 \
    python-multipart>=0.0.5

# Install remaining dependencies (skip problematic ones)
RUN pip install --no-cache-dir --user \
    pydantic==2.5.0 \
    sqlalchemy==2.0.23 \
    alembic==1.13.1 \
    passlib[bcrypt]==1.7.4 \
    python-jose[cryptography]==3.3.0 \
    pandas==2.1.4 \
    pint==0.22 \
    pyzmq==25.1.2 \
    python-socketio==5.10.0 \
    tornado>=6.1 \
    pymavlink==2.4.37 \
    cryptography==39.0.2 \
    bcrypt==4.1.2 \
    structlog==23.2.0 \
    || echo "Some optional dependencies failed to install - continuing"

# ================================
# Stage 3: Application Build
# ================================
FROM python-deps AS app-builder

WORKDIR /app

# Copy demo application (skip setup.py for demo)
COPY --chown=dartplanner:dartplanner demos/web_demo/ ./web_demo/

# Copy source code for imports
COPY --chown=dartplanner:dartplanner src/ ./src/

# Copy configuration
COPY --chown=dartplanner:dartplanner config/ ./config/

# ================================
# Stage 4: Production Runtime
# ================================
FROM base AS production

# Security hardening
RUN apt-get update && apt-get install -y --no-install-recommends \
    dumb-init \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy Python environment from builder
COPY --from=app-builder /root/.local /home/dartplanner/.local

# Copy application
WORKDIR /app
COPY --from=app-builder --chown=dartplanner:dartplanner /app/src/ ./src/
COPY --from=app-builder --chown=dartplanner:dartplanner /app/web_demo/ ./web_demo/
COPY --from=app-builder --chown=dartplanner:dartplanner /app/config/ ./config/

# Create necessary directories
RUN mkdir -p /home/dartplanner/.dart_planner \
    && mkdir -p /home/dartplanner/.config \
    && mkdir -p /app/static \
    && mkdir -p /app/logs \
    && chown -R dartplanner:dartplanner /app \
    && chown -R dartplanner:dartplanner /home/dartplanner

# Switch to non-root user
USER dartplanner

# Environment configuration
ENV PATH=/home/dartplanner/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    DART_PLANNER_MODE=production \
    DART_LOG_LEVEL=INFO \
    DART_METRICS_ENABLED=true \
    DART_PERFORMANCE_MONITORING=true \
    MPLCONFIGDIR=/home/dartplanner/.config/matplotlib

# Performance optimizations
ENV MALLOC_ARENA_MAX=2 \
    MALLOC_MMAP_THRESHOLD_=131072 \
    MALLOC_TRIM_THRESHOLD_=131072 \
    MALLOC_TOP_PAD_=131072 \
    MALLOC_MMAP_MAX_=65536

# Security environment (will be overridden at runtime)
ENV DART_CORS_ORIGINS=["*"] \
    DART_RATE_LIMIT_ENABLED=true

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Labels for metadata
LABEL \
    org.opencontainers.image.title="DART-Planner Demo" \
    org.opencontainers.image.description="Production-ready autonomous drone navigation demo" \
    org.opencontainers.image.version="1.0.0" \
    org.opencontainers.image.authors="DART-Planner Team" \
    org.opencontainers.image.source="https://github.com/Pasqui1010/DART-Planner" \
    org.opencontainers.image.documentation="https://github.com/Pasqui1010/DART-Planner/blob/main/README.md"

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["python", "web_demo/app.py"]
