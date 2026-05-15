# Janakpur Bolts Analytics - Quick Start Script
# Windows PowerShell version

Write-Host "🏏 Janakpur Bolts Analytics - Environment Setup" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "✅ Docker found" -ForegroundColor Green
    docker --version
} else {
    Write-Host "❌ Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "   Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ .env file created" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Update passwords in .env file before production!" -ForegroundColor Red
    Write-Host "   Edit .env and change:" -ForegroundColor Yellow
    Write-Host "   - POSTGRES_PASSWORD" -ForegroundColor Yellow
    Write-Host "   - PGADMIN_PASSWORD" -ForegroundColor Yellow
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

Write-Host ""

# Start Docker services
Write-Host "Starting Docker services..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker services started successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to start Docker services" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Wait for PostgreSQL
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check if PostgreSQL is up
Write-Host "Testing PostgreSQL connection..." -ForegroundColor Yellow
$maxRetries = 5
$retryCount = 0
$connected = $false

while (-not $connected -and $retryCount -lt $maxRetries) {
    $retryCount++
    Write-Host "  Attempt $retryCount/$maxRetries..." -ForegroundColor Gray
    
    $result = docker-compose exec -T postgres pg_isready -U bolts_admin 2>&1
    if ($LASTEXITCODE -eq 0) {
        $connected = $true
        Write-Host "✅ PostgreSQL is ready" -ForegroundColor Green
    } else {
        Start-Sleep -Seconds 5
    }
}

if (-not $connected) {
    Write-Host "❌ PostgreSQL failed to start. Check logs with: docker-compose logs postgres" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "✅ Environment is ready!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Show access points
Write-Host "📊 Access Points:" -ForegroundColor Cyan
Write-Host "   PostgreSQL:  localhost:5432" -ForegroundColor White
Write-Host "   PgAdmin:     http://localhost:5050" -ForegroundColor White
Write-Host "   Streamlit:   http://localhost:8501" -ForegroundColor White
Write-Host "   Redis:       localhost:6379" -ForegroundColor White
Write-Host ""

Write-Host "🔑 Default Credentials (CHANGE THESE!):" -ForegroundColor Yellow
Write-Host "   PostgreSQL:  bolts_admin / replace_me" -ForegroundColor Gray
Write-Host "   PgAdmin:     admin@bolts.np / replace_me" -ForegroundColor Gray
Write-Host ""

Write-Host "📝 Useful Commands:" -ForegroundColor Cyan
Write-Host "   View logs:       docker-compose logs -f" -ForegroundColor White
Write-Host "   Stop services:   docker-compose down" -ForegroundColor White
Write-Host "   Restart:         docker-compose restart" -ForegroundColor White
Write-Host "   Database shell:  docker-compose exec postgres psql -U bolts_admin -d bolts_analytics" -ForegroundColor White
Write-Host ""

Write-Host "🚀 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Open browser: http://localhost:8501" -ForegroundColor White
Write-Host "   2. Complete data source audit (see context/data_source_audit.md)" -ForegroundColor White
Write-Host "   3. Start ingesting match data" -ForegroundColor White
Write-Host ""
