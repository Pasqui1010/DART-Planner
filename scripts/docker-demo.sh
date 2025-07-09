#!/bin/bash

# ================================
# DART-Planner Docker Demo Manager
# Comprehensive script for managing Docker deployments
# ================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
DOCKER_COMPOSE_DEV_FILE="${PROJECT_ROOT}/docker-compose.dev.yml"
DOCKER_COMPOSE_DEMO_FILE="${PROJECT_ROOT}/docker-compose.demo.yml"

# Logo and header
print_logo() {
    echo -e "${CYAN}"
    echo "  ██████╗  █████╗ ██████╗ ████████╗    ██████╗ ██╗      █████╗ ███╗   ███╗███╗   ██╗███████╗██████╗ "
    echo "  ██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝    ██╔══██╗██║     ██╔══██╗████╗ ████║████╗  ██║██╔════╝██╔══██╗"
    echo "  ██║  ██║███████║██████╔╝   ██║       ██████╔╝██║     ███████║██╔████╔██║██╔██╗ ██║█████╗  ██████╔╝"
    echo "  ██║  ██║██╔══██║██╔══██╗   ██║       ██╔═══╝ ██║     ██╔══██║██║╚██╔╝██║██║╚██╗██║██╔══╝  ██╔══██╗"
    echo "  ██████╔╝██║  ██║██║  ██║   ██║       ██║     ███████╗██║  ██║██║ ╚═╝ ██║██║ ╚████║███████╗██║  ██║"
    echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝       ╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${BLUE}🚁 Production-Ready Autonomous Drone Navigation System${NC}"
    echo -e "${YELLOW}⚡ Docker Demo Management Script${NC}"
    echo ""
}

# Help message
print_help() {
    echo -e "${GREEN}Usage:${NC} $0 [COMMAND] [OPTIONS]"
    echo ""
    echo -e "${YELLOW}COMMANDS:${NC}"
    echo "  ${GREEN}start${NC}          Start the demo (production mode)"
    echo "  ${GREEN}start-dev${NC}      Start in development mode"
    echo "  ${GREEN}start-demo${NC}     Start in demo showcase mode"
    echo "  ${GREEN}stop${NC}           Stop all services"
    echo "  ${GREEN}restart${NC}        Restart all services"
    echo "  ${GREEN}logs${NC}           Show logs for all services"
    echo "  ${GREEN}status${NC}         Show status of all services"
    echo "  ${GREEN}build${NC}          Build all Docker images"
    echo "  ${GREEN}clean${NC}          Clean up containers and volumes"
    echo "  ${GREEN}health${NC}         Check health of all services"
    echo "  ${GREEN}benchmark${NC}      Run performance benchmarks"
    echo "  ${GREEN}test${NC}           Run test suite"
    echo "  ${GREEN}init${NC}           Initialize demo environment"
    echo "  ${GREEN}demo${NC}           Quick demo showcase"
    echo ""
    echo -e "${YELLOW}OPTIONS:${NC}"
    echo "  ${GREEN}--help, -h${NC}     Show this help message"
    echo "  ${GREEN}--verbose, -v${NC}  Enable verbose output"
    echo "  ${GREEN}--force, -f${NC}    Force operations (skip confirmations)"
    echo "  ${GREEN}--no-cache${NC}     Build without cache"
    echo ""
    echo -e "${YELLOW}EXAMPLES:${NC}"
    echo "  $0 start           # Start production demo"
    echo "  $0 start-dev       # Start development environment"
    echo "  $0 start-demo      # Start showcase demo"
    echo "  $0 logs dartplanner-app  # Show logs for specific service"
    echo "  $0 benchmark       # Run performance tests"
    echo "  $0 demo            # Quick 30-second demo"
    echo ""
    echo -e "${YELLOW}URLS (after starting):${NC}"
    echo "  Demo:              http://localhost:8080"
    echo "  Grafana:           http://localhost:3000"
    echo "  Prometheus:        http://localhost:9090"
    echo "  Documentation:     http://localhost:8000"
    echo ""
    echo -e "${CYAN}For more information, visit: https://github.com/Pasqui1010/DART-Planner${NC}"
}

# Utility functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Check if docker-compose is available
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        log_error "docker-compose is not installed. Please install docker-compose and try again."
        exit 1
    fi
}

# Wait for services to be healthy
wait_for_services() {
    local timeout=${1:-300}
    local interval=${2:-5}
    local elapsed=0
    
    log_info "Waiting for services to be healthy..."
    
    while [ $elapsed -lt $timeout ]; do
        if docker-compose ps | grep -q "Up (healthy)"; then
            log_success "Services are healthy!"
            return 0
        fi
        
        sleep $interval
        elapsed=$((elapsed + interval))
        echo -n "."
    done
    
    log_error "Timeout waiting for services to be healthy"
    return 1
}

# Initialize demo environment
init_demo() {
    log_info "Initializing DART-Planner demo environment..."
    
    # Create necessary directories
    mkdir -p "${PROJECT_ROOT}/logs"
    mkdir -p "${PROJECT_ROOT}/data"
    mkdir -p "${PROJECT_ROOT}/config/prometheus"
    mkdir -p "${PROJECT_ROOT}/config/grafana"
    mkdir -p "${PROJECT_ROOT}/config/nginx"
    
    # Generate environment file if it doesn't exist
    if [ ! -f "${PROJECT_ROOT}/.env" ]; then
        log_info "Creating .env file..."
        cat > "${PROJECT_ROOT}/.env" << EOF
# DART-Planner Environment Configuration
DART_SECRET_KEY=$(openssl rand -hex 32)
DART_PLANNER_MODE=production
DART_LOG_LEVEL=INFO
DART_METRICS_ENABLED=true
DART_PERFORMANCE_MONITORING=true
COMPOSE_PROJECT_NAME=dartplanner
EOF
    fi
    
    # Create basic Prometheus configuration
    if [ ! -f "${PROJECT_ROOT}/config/prometheus/prometheus.yml" ]; then
        log_info "Creating Prometheus configuration..."
        cat > "${PROJECT_ROOT}/config/prometheus/prometheus.yml" << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'dartplanner'
    static_configs:
      - targets: ['dartplanner-app:8080']
    metrics_path: '/metrics'
    scrape_interval: 5s
    
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF
    fi
    
    log_success "Demo environment initialized!"
}

# Start production demo
start_production() {
    log_info "Starting DART-Planner production demo..."
    
    cd "${PROJECT_ROOT}"
    
    if [ "$VERBOSE" = "true" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d --build
    else
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d --build > /dev/null 2>&1
    fi
    
    wait_for_services
    
    log_success "Production demo started successfully!"
    echo ""
    echo -e "${YELLOW}Demo URLs:${NC}"
    echo -e "  🚁 Main Demo:     ${CYAN}http://localhost:8080${NC}"
    echo -e "  📊 Grafana:       ${CYAN}http://localhost:3000${NC}"
    echo -e "  🔍 Prometheus:    ${CYAN}http://localhost:9090${NC}"
    echo -e "  🔄 Traefik:       ${CYAN}http://localhost:8081${NC}"
}

# Start development mode
start_development() {
    log_info "Starting DART-Planner development environment..."
    
    cd "${PROJECT_ROOT}"
    
    if [ "$VERBOSE" = "true" ]; then
        docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" up -d --build
    else
        docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" up -d --build > /dev/null 2>&1
    fi
    
    wait_for_services
    
    log_success "Development environment started successfully!"
    echo ""
    echo -e "${YELLOW}Development URLs:${NC}"
    echo -e "  🚁 Main App:      ${CYAN}http://localhost:8080${NC}"
    echo -e "  📓 Jupyter:       ${CYAN}http://localhost:8888${NC}"
    echo -e "  📊 Grafana:       ${CYAN}http://localhost:3000${NC}"
    echo -e "  🔍 Prometheus:    ${CYAN}http://localhost:9090${NC}"
    echo -e "  📧 MailHog:       ${CYAN}http://localhost:8025${NC}"
    echo -e "  📚 Docs:          ${CYAN}http://localhost:8000${NC}"
}

# Start demo showcase mode
start_demo_showcase() {
    log_info "Starting DART-Planner demo showcase..."
    
    cd "${PROJECT_ROOT}"
    
    if [ "$VERBOSE" = "true" ]; then
        docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" up -d --build
    else
        docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" up -d --build > /dev/null 2>&1
    fi
    
    wait_for_services
    
    log_success "Demo showcase started successfully!"
    echo ""
    echo -e "${YELLOW}Demo Showcase URLs:${NC}"
    echo -e "  🚁 Main Demo:     ${CYAN}http://localhost:8080${NC}"
    echo -e "  📊 Grafana:       ${CYAN}http://localhost:3000${NC}"
    echo -e "  📈 Analytics:     ${CYAN}http://localhost:8000${NC}"
    echo -e "  🔍 Prometheus:    ${CYAN}http://localhost:9091${NC}"
    echo -e "  💾 InfluxDB:      ${CYAN}http://localhost:8086${NC}"
    echo -e "  📦 CDN:           ${CYAN}http://localhost:8083${NC}"
}

# Stop all services
stop_services() {
    log_info "Stopping DART-Planner services..."
    
    cd "${PROJECT_ROOT}"
    
    # Stop all compose files
    docker-compose -f "$DOCKER_COMPOSE_FILE" down > /dev/null 2>&1 || true
    docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" down > /dev/null 2>&1 || true
    docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" down > /dev/null 2>&1 || true
    
    log_success "All services stopped!"
}

# Show logs
show_logs() {
    local service=${1:-}
    
    cd "${PROJECT_ROOT}"
    
    if [ -n "$service" ]; then
        log_info "Showing logs for service: $service"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f "$service" 2>/dev/null || \
        docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" logs -f "$service" 2>/dev/null || \
        docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" logs -f "$service" 2>/dev/null || \
        log_error "Service '$service' not found"
    else
        log_info "Showing logs for all services"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f 2>/dev/null || \
        docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" logs -f 2>/dev/null || \
        docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" logs -f 2>/dev/null || \
        log_error "No running services found"
    fi
}

# Check service status
check_status() {
    log_info "Checking service status..."
    
    cd "${PROJECT_ROOT}"
    
    echo -e "${YELLOW}Production Services:${NC}"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps 2>/dev/null || echo "Not running"
    echo ""
    
    echo -e "${YELLOW}Development Services:${NC}"
    docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" ps 2>/dev/null || echo "Not running"
    echo ""
    
    echo -e "${YELLOW}Demo Services:${NC}"
    docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" ps 2>/dev/null || echo "Not running"
}

# Build images
build_images() {
    log_info "Building Docker images..."
    
    cd "${PROJECT_ROOT}"
    
    local build_args=""
    if [ "$NO_CACHE" = "true" ]; then
        build_args="--no-cache"
    fi
    
    docker-compose -f "$DOCKER_COMPOSE_FILE" build $build_args
    docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" build $build_args
    docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" build $build_args
    
    log_success "Images built successfully!"
}

# Clean up containers and volumes
clean_up() {
    if [ "$FORCE" != "true" ]; then
        echo -e "${YELLOW}This will remove all DART-Planner containers and volumes.${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Cleanup cancelled."
            return 0
        fi
    fi
    
    log_info "Cleaning up containers and volumes..."
    
    cd "${PROJECT_ROOT}"
    
    # Stop and remove containers
    docker-compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
    docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" down -v --remove-orphans 2>/dev/null || true
    docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" down -v --remove-orphans 2>/dev/null || true
    
    # Remove unused images
    docker image prune -f --filter label="com.docker.compose.project=dartplanner" 2>/dev/null || true
    
    log_success "Cleanup completed!"
}

# Check health of services
check_health() {
    log_info "Checking health of services..."
    
    local services=(
        "http://localhost:8080/api/health"
        "http://localhost:3000/api/health"
        "http://localhost:9090/-/healthy"
    )
    
    for service in "${services[@]}"; do
        if curl -s -f "$service" > /dev/null 2>&1; then
            log_success "✓ $service"
        else
            log_error "✗ $service"
        fi
    done
}

# Run performance benchmarks
run_benchmarks() {
    log_info "Running performance benchmarks..."
    
    cd "${PROJECT_ROOT}"
    
    # Check if demo is running
    if ! curl -s -f "http://localhost:8080/api/health" > /dev/null 2>&1; then
        log_error "Demo is not running. Please start the demo first."
        exit 1
    fi
    
    # Run load test
    docker-compose -f "$DOCKER_COMPOSE_DEMO_FILE" --profile load-testing up load-tester
    
    log_success "Benchmarks completed! Check results in load_test_results volume."
}

# Run test suite
run_tests() {
    log_info "Running test suite..."
    
    cd "${PROJECT_ROOT}"
    
    docker-compose -f "$DOCKER_COMPOSE_DEV_FILE" --profile testing up test-runner
    
    log_success "Tests completed!"
}

# Quick demo showcase
quick_demo() {
    log_info "Starting quick DART-Planner demo showcase..."
    
    init_demo
    start_production
    
    echo ""
    echo -e "${GREEN}🎉 DART-Planner Demo is now running!${NC}"
    echo ""
    echo -e "${YELLOW}What to do next:${NC}"
    echo -e "  1. Open ${CYAN}http://localhost:8080${NC} in your browser"
    echo -e "  2. Select a demo scenario (e.g., 'Obstacle Avoidance')"
    echo -e "  3. Click 'Start Demo' to see autonomous navigation"
    echo -e "  4. Watch real-time metrics and 3D visualization"
    echo ""
    echo -e "${BLUE}Key Features Demonstrated:${NC}"
    echo -e "  ✅ SE(3) MPC Planning (<10ms response time)"
    echo -e "  ✅ Explicit Geometric Mapping (no neural dependency)"
    echo -e "  ✅ Edge-First Autonomous Operation"
    echo -e "  ✅ Real-time 3D Trajectory Visualization"
    echo -e "  ✅ Production-Ready Performance Monitoring"
    echo ""
    echo -e "${GREEN}Demo running successfully! Press Ctrl+C to stop.${NC}"
}

# Main script logic
main() {
    # Parse command line arguments
    VERBOSE="false"
    FORCE="false"
    NO_CACHE="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_logo
                print_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -f|--force)
                FORCE="true"
                shift
                ;;
            --no-cache)
                NO_CACHE="true"
                shift
                ;;
            *)
                COMMAND="$1"
                shift
                ;;
        esac
    done
    
    # Show logo
    print_logo
    
    # Check prerequisites
    check_docker
    check_docker_compose
    
    # Execute command
    case "${COMMAND:-}" in
        start)
            init_demo
            start_production
            ;;
        start-dev)
            init_demo
            start_development
            ;;
        start-demo)
            init_demo
            start_demo_showcase
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            start_production
            ;;
        logs)
            show_logs "$2"
            ;;
        status)
            check_status
            ;;
        build)
            build_images
            ;;
        clean)
            clean_up
            ;;
        health)
            check_health
            ;;
        benchmark)
            run_benchmarks
            ;;
        test)
            run_tests
            ;;
        init)
            init_demo
            ;;
        demo)
            quick_demo
            ;;
        *)
            log_error "Unknown command: ${COMMAND:-}"
            echo ""
            print_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 