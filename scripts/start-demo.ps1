# ================================
# DART-Planner Demo Startup Script (Windows)
# ================================

param(
    [string]$Mode = "demo",
    [switch]$Docker = $false,
    [switch]$Build = $false,
    [switch]$Help = $false
)

# Colors for output
$Red = 'Red'
$Green = 'Green'
$Yellow = 'Yellow'
$Blue = 'Blue'
$Cyan = 'Cyan'

function Write-Logo {
    Write-Host "DART-Planner Demo" -ForegroundColor $Cyan -NoNewline
    Write-Host " - Production-Ready Autonomous Drone Navigation" -ForegroundColor $Blue
    Write-Host "Demo Startup Script (Windows)" -ForegroundColor $Yellow
    Write-Host ""
}

function Write-Help {
    Write-Host "Usage: .\start-demo.ps1 [OPTIONS]" -ForegroundColor $Green
    Write-Host ""
    Write-Host "OPTIONS:" -ForegroundColor $Yellow
    Write-Host "  -Mode MODE         Demo mode: demo, dev, production (default: demo)" -ForegroundColor $Green
    Write-Host "  -Docker            Use Docker containers" -ForegroundColor $Green
    Write-Host "  -Build             Build Docker images" -ForegroundColor $Green
    Write-Host "  -Help              Show this help message" -ForegroundColor $Green
    Write-Host ""
    Write-Host "EXAMPLES:" -ForegroundColor $Yellow
    Write-Host "  .\start-demo.ps1                    # Start demo locally" -ForegroundColor $Green
    Write-Host "  .\start-demo.ps1 -Docker           # Start demo with Docker" -ForegroundColor $Green
    Write-Host "  .\start-demo.ps1 -Mode dev -Docker # Start development environment" -ForegroundColor $Green
    Write-Host ""
    Write-Host "URLS (after starting):" -ForegroundColor $Yellow
    Write-Host "  Demo:              http://localhost:8080" -ForegroundColor $Green
    Write-Host "  Grafana:           http://localhost:3000" -ForegroundColor $Green
    Write-Host "  Prometheus:        http://localhost:9090" -ForegroundColor $Green
    Write-Host ""
}

function Test-Docker {
    try {
        $dockerVersion = docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Docker is available: $dockerVersion" -ForegroundColor $Green
            return $true
        }
    } catch {
        Write-Host "Docker is not available" -ForegroundColor $Red
        return $false
    }
    return $false
}

function Test-Python {
    try {
        $pythonVersion = python --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Python is available: $pythonVersion" -ForegroundColor $Green
            return $true
        }
    } catch {
        Write-Host "Python is not available" -ForegroundColor $Red
        return $false
    }
    return $false
}

function Start-LocalDemo {
    Write-Host "Starting DART-Planner Demo (Local Mode)" -ForegroundColor $Blue
    
    # Check Python
    if (-not (Test-Python)) {
        Write-Host "Python is required for local demo" -ForegroundColor $Red
        return
    }
    
    # Install dependencies if needed
    Write-Host "Checking dependencies..." -ForegroundColor $Blue
    try {
        python -c "import fastapi, uvicorn" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Installing required dependencies..." -ForegroundColor $Yellow
            pip install fastapi uvicorn[standard] websockets numpy
        }
    } catch {
        Write-Host "Installing required dependencies..." -ForegroundColor $Yellow
        pip install fastapi uvicorn[standard] websockets numpy
    }
    
    # Start the demo
    Write-Host "Starting demo server..." -ForegroundColor $Blue
    Set-Location "demos/web_demo"
    
    try {
        python app.py
    } catch {
        Write-Host "Failed to start demo server" -ForegroundColor $Red
        Write-Host "Error: $_" -ForegroundColor $Red
    }
}

function Start-DockerDemo {
    Write-Host "Starting DART-Planner Demo (Docker Mode)" -ForegroundColor $Blue
    
    # Check Docker
    if (-not (Test-Docker)) {
        Write-Host "Docker is required for Docker mode" -ForegroundColor $Red
        return
    }
    
    # Build if requested
    if ($Build) {
        Write-Host "Building Docker images..." -ForegroundColor $Blue
        docker build -t dart-planner-demo -f demos/Dockerfile .
    }
    
    # Choose compose file based on mode
    $composeFile = switch ($Mode) {
        "dev" { "docker-compose.dev.yml" }
        "demo" { "docker-compose.demo.yml" }
        "production" { "docker-compose.yml" }
        default { "docker-compose.yml" }
    }
    
    Write-Host "Using compose file: $composeFile" -ForegroundColor $Blue
    
    # Start services
    Write-Host "Starting Docker services..." -ForegroundColor $Blue
    try {
        docker-compose -f $composeFile up -d
        
        Write-Host "Demo started successfully!" -ForegroundColor $Green
        Write-Host ""
        Write-Host "Access the demo at:" -ForegroundColor $Yellow
        Write-Host "  Demo:              http://localhost:8080" -ForegroundColor $Green
        Write-Host "  Grafana:           http://localhost:3000" -ForegroundColor $Green
        Write-Host "  Prometheus:        http://localhost:9090" -ForegroundColor $Green
        Write-Host ""
        Write-Host "To view logs: docker-compose -f $composeFile logs -f" -ForegroundColor $Blue
        Write-Host "To stop: docker-compose -f $composeFile down" -ForegroundColor $Blue
        
    } catch {
        Write-Host "Failed to start Docker services" -ForegroundColor $Red
        Write-Host "Error: $_" -ForegroundColor $Red
    }
}

# Main execution
Clear-Host
Write-Logo

if ($Help) {
    Write-Help
    exit 0
}

Write-Host "Demo Configuration:" -ForegroundColor $Blue
Write-Host "  Mode:              $Mode" -ForegroundColor $Green
Write-Host "  Docker:            $Docker" -ForegroundColor $Green
Write-Host "  Build:             $Build" -ForegroundColor $Green
Write-Host ""

if ($Docker) {
    Start-DockerDemo
} else {
    Start-LocalDemo
}

Write-Host ""
Write-Host "Demo startup complete!" -ForegroundColor $Green 