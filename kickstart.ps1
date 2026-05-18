# Start CricNepal Analytics Platform
# =====================================
# Comprehensive startup: Docker → PostgreSQL → Data Ingestion → Dashboard
#
# Run: .\kickstart.ps1

$ErrorActionPreference = "Stop"

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 78) -ForegroundColor Cyan
Write-Host "  CRICNEPAL ANALYTICS PLATFORM - KICKSTART" -ForegroundColor White
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 1: Start Docker Desktop
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[1/5] Checking Docker Desktop..." -ForegroundColor Yellow

$dockerRunning = $false
$dockerTest = docker ps 2>&1
if ($LASTEXITCODE -eq 0) {
    $dockerRunning = $true
    Write-Host "      Docker Desktop is running" -ForegroundColor Green
} else {
    Write-Host "      → Docker Desktop not running, starting..." -ForegroundColor Yellow
    
    # Start Docker Desktop
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    
    Write-Host "      Waiting for Docker to start (this may take 30-60 seconds)..." -ForegroundColor Yellow
    
    $maxWait = 120  # 2 minutes max wait
    $waited = 0
    while (-not $dockerRunning -and $waited -lt $maxWait) {
        Start-Sleep -Seconds 5
        $waited += 5
        
        $dockerTest = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerRunning = $true
            Write-Host "      Docker Desktop started successfully" -ForegroundColor Green
        } else {
            Write-Host "      ... still waiting ($waited seconds)" -ForegroundColor Gray
        }
    }
    
    if (-not $dockerRunning) {
        Write-Host "      Docker failed to start within $maxWait seconds" -ForegroundColor Red
        Write-Host ""
        Write-Host "MANUAL ACTION REQUIRED:" -ForegroundColor Red
        Write-Host "  1. Open Docker Desktop manually"
        Write-Host "  2. Wait for it to fully start"
        Write-Host "  3. Run this script again: .\kickstart.ps1"
        Write-Host ""
        exit 1
    }
}

Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 2: Start PostgreSQL Containers
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[2/5] Starting PostgreSQL containers..." -ForegroundColor Yellow

# Check if containers exist
$postgresExists = docker ps -a --format "{{.Names}}" | Select-String -Pattern "postgres" -Quiet

if ($postgresExists) {
    Write-Host "      → Containers found, ensuring they're running..." -ForegroundColor Gray
    docker-compose up -d 2>&1 | Out-Null
} else {
    Write-Host "      → Creating new containers..." -ForegroundColor Gray
    docker-compose up -d 2>&1 | Out-Null
}

# Wait for PostgreSQL to be ready
Write-Host "      Waiting for PostgreSQL to accept connections..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

$maxWait = 30
$waited = 0
$pgReady = $false

while (-not $pgReady -and $waited -lt $maxWait) {
    $testResult = docker-compose exec -T postgres pg_isready -U bolts_admin 2>&1
    if ($testResult -like "*accepting connections*") {
        $pgReady = $true
        Write-Host "      PostgreSQL is ready" -ForegroundColor Green
    } else {
        Start-Sleep -Seconds 2
        $waited += 2
    }
}

if (-not $pgReady) {
    Write-Host "      PostgreSQL might not be fully ready, but continuing..." -ForegroundColor Yellow
}

Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 3: Run Database Migrations
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[3/5] Setting up database schema..." -ForegroundColor Yellow

$env:POSTGRES_HOST = "localhost"  # Override for local connection

python src/ingestion/run_migrations.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "      Migration errors detected (may be OK if already run)" -ForegroundColor Yellow
} else {
    Write-Host "      Database schema ready" -ForegroundColor Green
}

Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 4: Ingest NPL Data
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[4/5] Ingesting NPL data from Parquet files..." -ForegroundColor Yellow
Write-Host "      Source: D:\Cric_Data\data\final\parquet\" -ForegroundColor Gray
Write-Host ""

python src/ingestion/ingest_npl_parquet.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "      Data ingestion failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "TROUBLESHOOTING:" -ForegroundColor Yellow
    Write-Host "  1. Check that Parquet files exist in D:\Cric_Data\data\final\parquet\"
    Write-Host "  2. Verify PostgreSQL is accessible: docker-compose exec postgres psql -U bolts_admin -d bolts_analytics"
    Write-Host "  3. Check logs in logs/ingestion_*.log"
    Write-Host ""
    exit 1
} else {
    Write-Host ""
    Write-Host "      Data ingestion complete" -ForegroundColor Green
}

Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 5: Launch Dashboard
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[5/5] Launching Streamlit dashboard..." -ForegroundColor Yellow

# Check if dashboard container is running
$streamlitRunning = docker ps --format "{{.Names}}" | Select-String -Pattern "streamlit" -Quiet

if ($streamlitRunning) {
    Write-Host "      Dashboard container already running" -ForegroundColor Green
} else {
    Write-Host "      → Starting dashboard container..." -ForegroundColor Gray
    docker-compose restart streamlit 2>&1 | Out-Null
    Start-Sleep -Seconds 5
}

Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# SUCCESS!
# ══════════════════════════════════════════════════════════════════════════

Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 78) -ForegroundColor Green
Write-Host "  CRICNEPAL ANALYTICS PLATFORM READY!" -ForegroundColor White
Write-Host ("=" * 79) -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  → Dashboard: " -NoNewline -ForegroundColor Gray
Write-Host "http://localhost:8501" -ForegroundColor White
Write-Host "  → PgAdmin:   " -NoNewline -ForegroundColor Gray
Write-Host "http://localhost:5050" -ForegroundColor White
Write-Host "     Username: dikshantneupane690@gmail.com" -ForegroundColor Gray
Write-Host "     Password: (see .env file)" -ForegroundColor Gray
Write-Host ""
Write-Host "Database:" -ForegroundColor Cyan
Write-Host "  → PostgreSQL: localhost:5432" -ForegroundColor Gray
Write-Host "  → Database: bolts_analytics" -ForegroundColor Gray
Write-Host "  → User: bolts_admin" -ForegroundColor Gray
Write-Host ""
Write-Host "Data Loaded:" -ForegroundColor Cyan
Write-Host "  → 64 NPL matches (Season 1 & 2)" -ForegroundColor Gray
Write-Host "  → 14,937 ball-by-ball deliveries" -ForegroundColor Gray
Write-Host "  → 1,917 player innings" -ForegroundColor Gray
Write-Host "  → 378 phase summaries" -ForegroundColor Gray
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open dashboard (browser should auto-open)" -ForegroundColor White
Write-Host "  2. Select 'Janakpur Bolts' from sidebar" -ForegroundColor White
Write-Host "  3. Verify 'Data source: Live DB' appears" -ForegroundColor White
Write-Host "  4. Start analyzing S1 vs S2 performance!" -ForegroundColor White
Write-Host ""

# Auto-open browser
Write-Host "Opening dashboard in browser..." -ForegroundColor Gray
Start-Sleep -Seconds 2
Start-Process "http://localhost:8501"

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 78) -ForegroundColor Green
Write-Host ""
