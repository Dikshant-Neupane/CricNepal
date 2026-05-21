# S3 Data Pipeline Strategy

**Recommendation:** Batch Processing ✅  
**Frequency:** Daily updates (post-match)  
**Real-time:** Not worth the complexity

---

## Why Batch Processing Wins

### Reality Check: Data Source Constraints
1. **Cricsheet:** Publishes match data 24-48 hours AFTER match ends
   - Not real-time
   - Batch JSON files
   - Your current ingestion pipeline is perfect for this

2. **ESPNcricinfo:** Live scores available, but:
   - No official API (must scrape HTML)
   - Rate limiting + IP blocks
   - Fragile (they change HTML structure frequently)
   - Legal gray area

3. **NPL Official:** May have live scores, but:
   - Unlikely to have developer API
   - Would need custom integration
   - Not worth effort for ~32 matches per season

### Use Case Analysis
**Do coaching staff need live updates during match?**
- ❌ NO — They're AT the match, watching with their eyes
- ✅ They need POST-MATCH analysis for next game prep

**What about opposition scouting?**
- ❌ Real-time doesn't help (opponent plays today, you play tomorrow)
- ✅ Batch processing gives you 12-24 hours to analyze before next match

---

## Recommended Pipeline: Daily Batch Updates

### Architecture
```
Every Day at 2 AM Nepal Time:
├── Check Cricsheet for new NPL data
├── Download new JSON files (if any)
├── Run ETL pipeline (D:\Cric_Data)
├── Transform to Parquet
├── Ingest to PostgreSQL (D:\CricNepal)
├── Dashboard auto-refreshes with new data
└── Send summary email to coaching staff
```

### Implementation

#### Option A: Manual (Acceptable for S3) ✅
```powershell
# Run this after each match day (takes 2 minutes)
cd D:\Cric_Data
.\.venv\Scripts\Activate.ps1

# Step 1: Download latest Cricsheet data
Invoke-WebRequest -Uri "https://cricsheet.org/downloads/npl_json.zip" -OutFile "data/npl_s3.zip"
Expand-Archive -Path "data/npl_s3.zip" -DestinationPath "data/npl_s3_raw" -Force

# Step 2: Run ETL
python etl/load_duckdb.py

# Step 3: Transform to schema
python etl/transform_to_schema.py

# Step 4: Ingest to PostgreSQL
cd D:\CricNepal
.\.venv\Scripts\Activate.ps1
python src/ingestion/ingest_npl_parquet.py

# Done! Dashboard now has latest data
```

**Effort:** 2 minutes per match day  
**Acceptable for:** 32-match season (8-10 match days)

#### Option B: Automated (Overkill but Cool) 🤖

**Windows Task Scheduler Script:**

<function_calls>
<invoke name="create_file">
<parameter name="content"># NPL S3 Automated Data Update
# ==============================
# Runs daily at 2 AM to check for new Cricsheet data
# Add to Windows Task Scheduler for automation

$ErrorActionPreference = "Stop"

# Paths
$CRIC_DATA = "D:\Cric_Data"
$CRIC_NEPAL = "D:\CricNepal"
$LOG_FILE = "$CRIC_NEPAL\logs\auto_update_$(Get-Date -Format 'yyyy-MM-dd').log"

function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -Append -FilePath $LOG_FILE
    Write-Host "$timestamp - $Message"
}

Write-Log "===== NPL S3 DATA UPDATE START ====="

# ═══════════════════════════════════════════════════════════════════
# Step 1: Download Latest Cricsheet Data
# ═══════════════════════════════════════════════════════════════════

Write-Log "Downloading latest NPL data from Cricsheet..."

try {
    $url = "https://cricsheet.org/downloads/npl_json.zip"
    $tempZip = "$CRIC_DATA\data\npl_latest.zip"
    
    Invoke-WebRequest -Uri $url -OutFile $tempZip -ErrorAction Stop
    
    $currentSize = (Get-Item $tempZip).Length
    $previousSize = 0
    
    if (Test-Path "$CRIC_DATA\data\npl_previous_size.txt") {
        $previousSize = Get-Content "$CRIC_DATA\data\npl_previous_size.txt"
    }
    
    if ($currentSize -eq $previousSize) {
        Write-Log "No new data available (file size unchanged: $currentSize bytes)"
        Write-Log "===== UPDATE SKIPPED (NO NEW DATA) ====="
        exit 0
    }
    
    Write-Log "New data detected! Previous: $previousSize bytes, Current: $currentSize bytes"
    $currentSize | Out-File "$CRIC_DATA\data\npl_previous_size.txt"
    
} catch {
    Write-Log "ERROR: Failed to download Cricsheet data - $($_.Exception.Message)"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════
# Step 2: Extract and Process
# ═══════════════════════════════════════════════════════════════════

Write-Log "Extracting new match files..."

try {
    $extractPath = "$CRIC_DATA\data\npl_s3_raw"
    
    if (Test-Path $extractPath) {
        Remove-Item $extractPath -Recurse -Force
    }
    
    Expand-Archive -Path $tempZip -DestinationPath $extractPath -Force
    
    $matchCount = (Get-ChildItem $extractPath -Filter "*.json").Count
    Write-Log "Extracted $matchCount match files"
    
} catch {
    Write-Log "ERROR: Failed to extract files - $($_.Exception.Message)"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════
# Step 3: Run ETL Pipeline
# ═══════════════════════════════════════════════════════════════════

Write-Log "Running ETL pipeline (Cric_Data)..."

try {
    cd $CRIC_DATA
    & "$CRIC_DATA\.venv\Scripts\Activate.ps1"
    
    # Load to DuckDB
    python etl/load_duckdb.py 2>&1 | Out-File -Append -FilePath $LOG_FILE
    
    if ($LASTEXITCODE -ne 0) {
        throw "load_duckdb.py failed with exit code $LASTEXITCODE"
    }
    
    Write-Log "ETL Step 1 complete (DuckDB loaded)"
    
    # Transform to schema
    python etl/transform_to_schema.py 2>&1 | Out-File -Append -FilePath $LOG_FILE
    
    if ($LASTEXITCODE -ne 0) {
        throw "transform_to_schema.py failed with exit code $LASTEXITCODE"
    }
    
    Write-Log "ETL Step 2 complete (Schema transformed)"
    
} catch {
    Write-Log "ERROR: ETL pipeline failed - $($_.Exception.Message)"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════
# Step 4: Ingest to PostgreSQL
# ═══════════════════════════════════════════════════════════════════

Write-Log "Ingesting to PostgreSQL (CricNepal)..."

try {
    cd $CRIC_NEPAL
    & "$CRIC_DATA\.venv\Scripts\Activate.ps1"  # Reuse Cric_Data venv
    
    $env:POSTGRES_HOST = "localhost"
    python src/ingestion/ingest_npl_parquet.py 2>&1 | Out-File -Append -FilePath $LOG_FILE
    
    if ($LASTEXITCODE -ne 0) {
        throw "ingest_npl_parquet.py failed with exit code $LASTEXITCODE"
    }
    
    Write-Log "PostgreSQL ingestion complete"
    
} catch {
    Write-Log "ERROR: PostgreSQL ingestion failed - $($_.Exception.Message)"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════
# Step 5: Generate Summary Report
# ═══════════════════════════════════════════════════════════════════

Write-Log "Generating summary report..."

try {
    cd $CRIC_NEPAL
    
    # Query match counts
    $matchCountQuery = @"
SELECT 
    COUNT(*) as total_matches,
    COUNT(DISTINCT match_date) as match_days,
    MAX(match_date) as latest_match
FROM matches
WHERE season_name = 'Season 3';
"@
    
    # TODO: Run query and email results to coaching staff
    # For now, just log completion
    
    Write-Log "Summary: $matchCount new matches processed"
    
} catch {
    Write-Log "WARNING: Summary generation failed (non-critical)"
}

# ═══════════════════════════════════════════════════════════════════
# Success!
# ═══════════════════════════════════════════════════════════════════

Write-Log "===== NPL S3 DATA UPDATE COMPLETE ====="
Write-Log "Dashboard now has latest match data"

exit 0
