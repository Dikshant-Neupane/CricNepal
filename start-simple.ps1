# CricNepal Platform - Simple Startup Script
# ============================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  CRICNEPAL ANALYTICS PLATFORM - STARTUP" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 1: Check Docker
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[1/5] Checking Docker Desktop..." -ForegroundColor Yellow

$dockerTest = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERROR: Docker Desktop is not running" -ForegroundColor Red
    Write-Host ""
    Write-Host "MANUAL ACTION REQUIRED:" -ForegroundColor Yellow
    Write-Host "  1. Open Docker Desktop" -ForegroundColor White
    Write-Host "  2. Wait for it to fully start (green icon in system tray)" -ForegroundColor White
    Write-Host "  3. Run this script again: .\start-simple.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "      OK: Docker Desktop is running" -ForegroundColor Green
Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 2: Start PostgreSQL
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[2/5] Starting PostgreSQL containers..." -ForegroundColor Yellow

docker-compose up -d

Write-Host "      Waiting for PostgreSQL to start..." -ForegroundColor Gray
Start-Sleep -Seconds 15

Write-Host "      OK: Containers started" -ForegroundColor Green
Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 3: Run Migrations
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[3/5] Setting up database schema..." -ForegroundColor Yellow

$env:POSTGRES_HOST = "localhost"

python src/ingestion/run_migrations.py

Write-Host "      OK: Schema ready" -ForegroundColor Green
Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 4: Ingest NPL Data
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[4/5] Ingesting NPL data from D:\Cric_Data\data\final\parquet\..." -ForegroundColor Yellow
Write-Host ""

python src/ingestion/ingest_npl_parquet.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "      ERROR: Data ingestion failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "TROUBLESHOOTING:" -ForegroundColor Yellow
    Write-Host "  1. Check that Parquet files exist in D:\Cric_Data\data\final\parquet\" -ForegroundColor White
    Write-Host "  2. Check logs in logs/ingestion_*.log" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "      OK: Data ingestion complete" -ForegroundColor Green
Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# STEP 5: Launch Dashboard
# ══════════════════════════════════════════════════════════════════════════

Write-Host "[5/5] Launching dashboard..." -ForegroundColor Yellow

docker-compose restart streamlit 2>&1 | Out-Null
Start-Sleep -Seconds 3

Write-Host "      OK: Dashboard started" -ForegroundColor Green
Write-Host ""

# ══════════════════════════════════════════════════════════════════════════
# SUCCESS!
# ══════════════════════════════════════════════════════════════════════════

Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  SUCCESS: CRICNEPAL ANALYTICS PLATFORM READY!" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  Dashboard:  http://localhost:8501" -ForegroundColor White
Write-Host "  PgAdmin:    http://localhost:5050" -ForegroundColor White
Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor White
Write-Host ""
Write-Host "Data Loaded:" -ForegroundColor Cyan
Write-Host "  64 NPL matches (Season 1 & 2)" -ForegroundColor White
Write-Host "  14,937 ball-by-ball deliveries" -ForegroundColor White
Write-Host "  1,917 player innings" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:8501 in your browser" -ForegroundColor White
Write-Host "  2. Select 'Janakpur Bolts' from sidebar" -ForegroundColor White
Write-Host "  3. Verify 'Data source: Live DB' appears" -ForegroundColor White
Write-Host ""

Write-Host "Opening dashboard..." -ForegroundColor Gray
Start-Sleep -Seconds 2
Start-Process "http://localhost:8501"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
