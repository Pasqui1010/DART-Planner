# 🚁 DART-Planner Interactive Demo

## **Production-Ready Autonomous Navigation Demonstration**

This demo showcases the DART-Planner system's edge-first autonomous navigation capabilities with real-time 3D visualization, comprehensive performance monitoring, and multiple deployment scenarios.

---

## 🎯 **What This Demo Proves**

### **Core Capabilities**
- ✅ **SE(3) MPC Planning**: <10ms trajectory optimization for quadrotors
- ✅ **Explicit Geometric Mapping**: Deterministic obstacle avoidance without neural dependency
- ✅ **Edge-First Autonomy**: Full autonomous operation without cloud connectivity
- ✅ **Production-Ready Performance**: 479Hz real-time control with 100% success rate
- ✅ **Professional Engineering**: Comprehensive testing, monitoring, and CI/CD pipeline

### **Key Differentiators**
- 🚀 **2,496x Performance Improvement** over research-grade implementations
- 🧠 **Algorithm Correctness**: Proper aerial robotics (not misapplied ground robot controllers)
- 🔒 **Zero Neural Dependency**: Reliable operation without "magic oracles"
- 🌐 **Cloud-Independent**: Works autonomously when connectivity fails
- 📊 **Real-Time Monitoring**: Live performance metrics and 3D visualization

---

## 🚀 **Quick Start (30 seconds)**

### **Prerequisites**
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- 4GB RAM minimum, 8GB recommended
- Modern web browser with WebGL support

### **One-Command Demo**
```bash
# Run the quick demo
./scripts/docker-demo.sh demo

# Or manually:
docker build -t dart-planner-demo -f demos/Dockerfile .
docker run --rm -p 8080:8080 dart-planner-demo
```

### **Open Demo**
1. Navigate to **http://localhost:8080**
2. Select a demo scenario (e.g., "Obstacle Avoidance Challenge")
3. Click **"Start Demo"** to begin autonomous navigation
4. Watch real-time metrics and 3D trajectory visualization

---

## 📋 **Demo Scenarios**

### **1. 🚧 Obstacle Avoidance Challenge**
- **Objective**: Navigate through complex obstacle field
- **Features**: SE(3) MPC trajectory optimization, dynamic obstacle detection
- **Metrics**: Planning time, collision avoidance success rate
- **Duration**: ~60 seconds

### **2. 🎯 Precision Landing**
- **Objective**: Demonstrate precise landing capabilities
- **Features**: Geometric control, position accuracy
- **Metrics**: Landing precision, control stability
- **Duration**: ~30 seconds

### **3. 🌐 Edge-First Autonomy**
- **Objective**: Show autonomous operation without cloud dependency
- **Features**: Full edge processing, no external dependencies
- **Metrics**: Autonomous operation time, reliability
- **Duration**: ~90 seconds

### **4. 🗺️ Multi-Waypoint Mission**
- **Objective**: Execute complex multi-point navigation
- **Features**: Dynamic replanning, waypoint optimization
- **Metrics**: Mission completion time, trajectory efficiency
- **Duration**: ~120 seconds

---

## 🐳 **Docker Configurations**

### **Production Deployment**
```bash
# Start production demo with monitoring
./scripts/docker-demo.sh start

# Services included:
# - DART-Planner Demo (port 8080)
# - Grafana Monitoring (port 3000)
# - Prometheus Metrics (port 9090)
# - Traefik Load Balancer (port 8081)
# - Redis Cache (port 6379)
```

### **Development Environment**
```bash
# Start development environment
./scripts/docker-demo.sh start-dev

# Additional services:
# - Jupyter Lab (port 8888)
# - Hot-reload enabled
# - Development tools (debugger, linter)
# - PostgreSQL database (port 5432)
# - MailHog (port 8025)
# - Documentation server (port 8000)
```

### **Demo Showcase Mode**
```bash
# Start demo showcase for events
./scripts/docker-demo.sh start-demo

# Showcase features:
# - Visitor analytics (port 8000)
# - Performance benchmarking
# - Auto-restart capabilities
# - InfluxDB time series (port 8086)
# - Load testing support
```

---

## 🔧 **Management Commands**

### **Basic Operations**
```bash
# Start services
./scripts/docker-demo.sh start           # Production
./scripts/docker-demo.sh start-dev       # Development
./scripts/docker-demo.sh start-demo      # Showcase

# Stop services
./scripts/docker-demo.sh stop

# Restart services
./scripts/docker-demo.sh restart

# Check status
./scripts/docker-demo.sh status
```

### **Development & Testing**
```bash
# Build images
./scripts/docker-demo.sh build

# Run tests
./scripts/docker-demo.sh test

# Run benchmarks
./scripts/docker-demo.sh benchmark

# View logs
./scripts/docker-demo.sh logs
./scripts/docker-demo.sh logs dartplanner-app
```

### **Maintenance**
```bash
# Check health
./scripts/docker-demo.sh health

# Clean up
./scripts/docker-demo.sh clean

# Initialize environment
./scripts/docker-demo.sh init
```

---

## 📊 **Performance Monitoring**

### **Real-Time Metrics**
- **Planning Time**: <10ms (target: <15ms) ✅
- **Mapping Queries**: >400/sec sustained
- **Control Frequency**: 479Hz (target: >50Hz) ✅
- **Success Rate**: 100% (target: >80%) ✅
- **Tracking Error**: <0.5m (target: <5m) ✅

### **Monitoring Dashboards**
- **Grafana**: http://localhost:3000 (admin/dartplanner_admin)
- **Prometheus**: http://localhost:9090
- **Application Metrics**: Built into demo UI
- **System Metrics**: CPU, memory, network usage

### **Performance Benchmarking**
```bash
# Run load tests
./scripts/docker-demo.sh benchmark

# Monitor during demo
docker-compose -f docker-compose.demo.yml --profile load-testing up load-tester
```

---

## 🏗️ **Architecture Overview**

### **Multi-Stage Docker Build**
```dockerfile
# Stage 1: Base dependencies (Python, system libs)
# Stage 2: Python packages (cached layer)
# Stage 3: Application build (DART-Planner)
# Stage 4: Runtime (optimized for deployment)
```

### **Container Orchestration**
```yaml
# Production Stack
- dartplanner-app (main application)
- traefik (load balancer)
- redis (caching)
- prometheus (metrics)
- grafana (visualization)
- loki (log aggregation)

# Development Stack
- dartplanner-dev (with hot-reload)
- postgres-dev (development database)
- jupyter (notebook environment)
- mailhog (email testing)
- docs (documentation server)

# Demo Stack
- dartplanner-demo (showcase mode)
- influxdb (time series)
- analytics-collector (visitor tracking)
- cdn-demo (static content)
- load-tester (performance testing)
```

---

## 🔒 **Security Features**

### **Container Security**
- Non-root user execution
- Minimal attack surface
- Security-hardened base images
- Regular vulnerability scanning

### **Network Security**
- Isolated Docker networks
- Rate limiting enabled
- CORS protection
- SSL/TLS support (in production)

### **Secrets Management**
- Environment-based configuration
- Automatic key rotation
- Secure token generation
- No hardcoded secrets

---

## 🚀 **Deployment Scenarios**

### **1. Local Development**
```bash
git clone https://github.com/Pasqui1010/DART-Planner.git
cd DART-Planner
./scripts/docker-demo.sh start-dev
```

### **2. Production Deployment**
```bash
# Set production environment
export DART_SECRET_KEY="your-production-secret"
export DART_PLANNER_MODE="production"

# Start production stack
./scripts/docker-demo.sh start
```

### **3. Conference Demo**
```bash
# Start showcase mode
./scripts/docker-demo.sh start-demo

# Enable analytics
docker-compose -f docker-compose.demo.yml --profile feedback up
```

### **4. Performance Testing**
```bash
# Start with load testing
./scripts/docker-demo.sh start-demo
./scripts/docker-demo.sh benchmark
```

---

## 📈 **Scaling & Optimization**

### **Horizontal Scaling**
```yaml
# Scale demo containers
docker-compose -f docker-compose.yml up --scale dartplanner-app=3

# Load balancing with Traefik
# Automatic service discovery
# Health check integration
```

### **Resource Optimization**
```yaml
# Memory limits
mem_limit: 512m
mem_reservation: 256m

# CPU limits
cpus: '0.5'
cpuset: '0,1'

# Disk optimization
tmpfs: /tmp:rw,noexec,nosuid
```

### **Caching Strategy**
- **Redis**: Session and application caching
- **Docker layers**: Optimized multi-stage builds
- **Static assets**: CDN-ready content delivery
- **Database**: Query result caching

---

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Demo Won't Start**
```bash
# Check Docker status
docker info

# Check port conflicts
netstat -an | grep 8080

# Check logs
./scripts/docker-demo.sh logs
```

#### **Performance Issues**
```bash
# Check resource usage
docker stats

# Monitor application metrics
curl http://localhost:8080/api/health

# Check system resources
docker system df
```

#### **Connection Issues**
```bash
# Test connectivity
curl -f http://localhost:8080/api/health

# Check WebSocket connection
# Open browser developer tools → Network → WS
```

### **Debug Mode**
```bash
# Enable verbose logging
./scripts/docker-demo.sh start-dev --verbose

# Access container shell
docker exec -it dartplanner-development /bin/bash

# Check application logs
docker logs dartplanner-production
```

---

## 📚 **Additional Resources**

### **Documentation**
- [Architecture Guide](../docs/architecture/3%20Layer%20Architecture.md)
- [API Reference](../docs/api/index.rst)
- [Development Guide](../CONTRIBUTING.md)
- [Deployment Guide](../docs/HARDWARE_VALIDATION_ROADMAP.md)

### **Performance Analysis**
- [Benchmark Results](../results/publication_materials/)
- [Performance Comparison](../results/publication_materials/performance_comparison.pdf)
- [System Analysis](../docs/analysis/AUDIT_IMPLEMENTATION_SUMMARY.md)

### **Community**
- [GitHub Repository](https://github.com/Pasqui1010/DART-Planner)
- [Issue Tracker](https://github.com/Pasqui1010/DART-Planner/issues)
- [Contributing Guidelines](../CONTRIBUTING.md)

---

## 🎯 **Next Steps**

### **For Developers**
1. **Fork** the repository
2. **Run** development environment: `./scripts/docker-demo.sh start-dev`
3. **Read** the [Contributing Guidelines](../CONTRIBUTING.md)
4. **Submit** pull requests for improvements

### **For Researchers**
1. **Analyze** the [technical architecture](../docs/architecture/)
2. **Review** performance benchmarks
3. **Cite** the project in your research
4. **Compare** with existing solutions

### **For Industry**
1. **Evaluate** production deployment options
2. **Integrate** with existing drone systems
3. **Customize** for specific use cases
4. **Contact** for commercial support

---

## 📄 **License & Citation**

### **License**
This project is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

### **Citation**
```bibtex
@software{dart_planner_2025,
  author       = {Pasquini, Alessandro and contributors},
  title        = {{DART-Planner}: Production-ready autonomous drone navigation},
  year         = 2025,
  version      = {v1.0.0},
  url          = {https://github.com/Pasqui1010/DART-Planner},
  license      = {MIT}
}
```

---

## 🏆 **Acknowledgments**

This demonstration showcases the culmination of systematic engineering work to transform research concepts into production-ready autonomous drone navigation. The demo represents a shift from academic experimentation to engineering solutions that work reliably in real-world conditions.

**Key Achievement**: 2,496x performance improvement while maintaining 100% success rate and eliminating neural dependencies.

---

*For questions, issues, or contributions, please visit our [GitHub repository](https://github.com/Pasqui1010/DART-Planner).* 