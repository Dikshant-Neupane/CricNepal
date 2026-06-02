# Janakpur Bolts Analytics Dashboard — Operator Runbook

**Production Version:** v1.0  
**Last Updated:** June 2, 2026  
**Operator:** Cricket Analytics Team

---

## 1. Overview

The Janakpur Bolts Analytics Dashboard provides tactical intelligence for coaching staff, combining match records, player performance data, and phase-level analytics into decision-ready insights.

**Core Capabilities:**
- Executive KPI tracking (Win%, NRR, form index)
- S1 vs S2 comparative analysis with delta metrics
- Data quality monitoring and validation
- Decision intelligence with prioritized tactical recommendations
- Phase-level performance breakdown (Powerplay, Middle, Death)

**Technology Stack:**
- **Framework:** Streamlit 1.57.0
- **Python:** 3.14.3
- **Data Format:** Apache Parquet
- **Testing:** pytest 9.0.3 (40 integration tests, 214 total tests)

---

## 2. Data Refresh Procedures

### 2.1 Match Data Update

**Location:** `D:/Cric_Data/data/final/parquet/matches.parquet`

**Required Fields (10):**
- `season` (str): "S1", "S2", "S3"
- `competition_name` (str): Tournament name
- `competition_tier` (str): "Primary", "Secondary", "Tertiary"
- `opposition_strength_bucket` (str): "Tier 1", "Tier 2", "Tier 3"
- `match_context` (str): "League", "Playoff", "Final"
- `result` (str): "W", "L", "NR"
- `runs_for` (int): Runs scored by Janakpur Bolts
- `runs_against` (int): Runs scored by opposition
- `overs_faced` (float): Overs batted by Janakpur Bolts
- `overs_bowled` (float): Overs bowled by Janakpur Bolts

**Update Process:**
```bash
# 1. Validate new data has all required fields
python -c "
import pandas as pd
df = pd.read_parquet('D:/Cric_Data/data/final/parquet/matches.parquet')
required = ['season', 'competition_name', 'competition_tier', 'opposition_strength_bucket', 
            'match_context', 'result', 'runs_for', 'runs_against', 'overs_faced', 'overs_bowled']
missing = [f for f in required if f not in df.columns]
print('✅ All required fields present' if not missing else f'❌ Missing: {missing}')
"

# 2. Check data quality score
python -c "
from src.dashboard.services.data_quality import validate_match_records
from src.dashboard.services.data_source import load_match_records
df = load_match_records()
report = validate_match_records(df)
print(f\"Quality Score: {report['reliability_score']}/100 ({report['status']})\")
"

# 3. Run smoke tests to verify no regressions
.venv\Scripts\python.exe -m pytest tests/test_smoke_dashboard.py -v
```

**Quality Thresholds:**
- **Healthy:** 90-100 score (production ready)
- **Warning:** 70-89 score (review findings, may still deploy)
- **Critical:** <70 score (do not deploy, fix data issues)

### 2.2 Player Data Update

**Locations:**
- Player innings: `D:/Cric_Data/data/final/parquet/player_innings.parquet`
- Phase summary: `D:/Cric_Data/data/final/parquet/phase_summary.parquet`
- Roster: `D:/Cric_Data/data/player_rosters/npl_player_rosters_20260521.csv`

**Update Process:**
```bash
# Validate player data consistency
python -c "
import pandas as pd
players = pd.read_parquet('D:/Cric_Data/data/final/parquet/player_innings.parquet')
phases = pd.read_parquet('D:/Cric_Data/data/final/parquet/phase_summary.parquet')
print(f'Player records: {len(players)} innings')
print(f'Phase records: {len(phases)} phases')
print(f'Match coverage: {players[\"match_id\"].nunique()} matches')
"
```

### 2.3 Competition Weights

**File:** `src/dashboard/services/metrics.py` (lines 1-10)

**Current Weights:**
```python
COMPETITION_WEIGHTS = {
    "NPL Season 2": 0.50,
    "Koshi Province Oli Cup": 0.30,
    "NPL Season 1": 0.15,
    "President Cup": 0.05,
}
```

**Update Process:**
1. Edit weights in `src/dashboard/services/metrics.py`
2. Run weighted form index test: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py::test_compute_weighted_form_index_uses_competition_weights -v`
3. Restart dashboard to apply changes

---

## 3. Dashboard Startup

### 3.1 Standard Launch

```bash
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Launch dashboard on localhost:8501
streamlit run src/dashboard/app.py
```

**Expected Output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

### 3.2 Custom Port

```bash
streamlit run src/dashboard/app.py --server.port 8502
```

### 3.3 Production Deployment

```bash
# Run on specific port with caching
streamlit run src/dashboard/app.py --server.port 80 --server.enableCORS false --server.enableXsrfProtection true
```

---

## 4. KPI Calculation Reference

### 4.1 Team KPIs (Basic)

**Function:** `compute_team_kpis(df: pd.DataFrame) -> Dict`  
**Location:** `src/dashboard/services/metrics.py` (lines 30-60)

**Formulas:**
- **Win%:** `(Wins / Total Matches) * 100`
- **Net Run Rate (NRR):**  
  `(Total Runs For / Total Overs Faced) - (Total Runs Against / Total Overs Bowled)`
- **Avg Runs For:** `Total Runs For / Matches`
- **Avg Runs Against:** `Total Runs Against / Matches`

### 4.2 Season-Specific KPIs

**Function:** `compute_season_kpis(df: pd.DataFrame) -> Dict[str, Dict]`  
**Location:** `src/dashboard/services/metrics.py` (lines 63-115)

**Output Structure:**
```python
{
    "S1": {
        "matches": 8,
        "wins": 5,
        "losses": 3,
        "win_pct": 62.5,
        "nrr": 0.420,
        "avg_runs_for": 165.0,
        "avg_runs_against": 155.0
    },
    "S2": { ... }
}
```

### 4.3 Season Delta

**Function:** `compute_season_delta(season_kpis: Dict) -> Dict`  
**Location:** `src/dashboard/services/metrics.py` (lines 118-145)

**Calculations:**
- **Win% Delta:** `S2_win_pct - S1_win_pct`
- **NRR Delta:** `S2_nrr - S1_nrr`
- **Runs Delta:** `(S2_avg_runs_for - S1_avg_runs_for, S2_avg_runs_against - S1_avg_runs_against)`

### 4.4 Form Index

**Function:** `compute_form_index(df: pd.DataFrame, n: int = 5) -> float`  
**Location:** `src/dashboard/services/metrics.py` (lines 148-170)

**Formula:**  
`Form Index = (Wins in Last N Matches / N) * 100`

**Interpretation:**
- **80-100%:** Excellent form
- **60-79%:** Good form
- **40-59%:** Average form
- **<40%:** Poor form

### 4.5 Weighted Form Index

**Function:** `compute_weighted_form_index(df: pd.DataFrame, n: int = 5) -> float`  
**Location:** `src/dashboard/services/metrics.py` (lines 173-190)

**Formula:**  
`Weighted Form = Σ(Win_i × Competition_Weight_i) / N`

Uses `COMPETITION_WEIGHTS` to adjust for tournament quality.

---

## 5. Data Quality Monitoring

### 5.1 Validation Checks

**Service:** `validate_match_records(df: pd.DataFrame) -> Dict`  
**Location:** `src/dashboard/services/data_quality.py`

**Automated Checks:**
1. **Missing Required Fields** (ERROR, -20 points each)
2. **Invalid Competition Tiers** (ERROR, -20 points)
3. **Invalid Match Results** (ERROR, -20 points)
4. **Missing Opposition Strength** (WARNING, -8 points)
5. **Low Data Completeness** <80% (WARNING, -8 points)
6. **Zero Runs Detection** (WARNING, -8 points) — indicates missing ball-by-ball data
7. **Overs Validation** (ERROR, -20 points) — ensures T20 format (overs ≤ 20)
8. **Season Distribution** (INFO, 0 points) — reports multi-season coverage

### 5.2 Quality Score Calculation

**Formula:**  
`Score = 100 - (Errors × 20) - (Warnings × 8)`

**Status Mapping:**
- **Healthy:** ≥90
- **Warning:** 70-89
- **Critical:** <70

### 5.3 Dashboard Display

Quality report visible in **Executive Overview** page:
- Expandable "Data Contract Findings" card
- Color-coded by status (green/amber/red)
- Lists top 3 findings with details

---

## 6. Decision Intelligence System

### 6.1 Executive Recommendations

**Function:** `generate_executive_recommendations(season_kpis, quality_score)`  
**Location:** `src/dashboard/services/decision_intelligence.py` (lines 9-96)

**Priority Ranking:**
1. **Critical Win% Decline** (drop >30pp)
2. **High Win% Decline** (drop 15-30pp)
3. **NRR Efficiency Decline** (drop >0.5)
4. **Data Quality Issues** (score <90)
5. **Positive Momentum** (Win% improved >5pp)

**Output:** Ranked list of tactical priorities with S1/S2 delta context.

### 6.2 Phase Recommendations

**Function:** `generate_phase_recommendations(s1_stats, s2_stats, phase_name)`  
**Location:** `src/dashboard/services/decision_intelligence.py` (lines 99-180)

**Structure:**
- **Insight:** Data-driven observation with S1/S2 comparison
- **Risk:** Consequences of current trend
- **Action:** Specific tactical fix with measurable target

**Phases:**
- **Powerplay** (overs 1-6): Focus on run rate, dot%, intent
- **Middle** (overs 7-15): Focus on acceleration, rotation
- **Death** (overs 16-20): Focus on finishing, specialist allocation

---

## 7. Testing & Validation

### 7.1 Critical Test Suites

**Run Before Production Deploy:**
```bash
# Integration tests (40 tests, ~2s)
.venv\Scripts\python.exe -m pytest tests/test_smoke_dashboard.py tests/test_metrics.py tests/test_ui_patterns.py tests/test_data_quality.py tests/test_decision_intelligence.py -v

# Expected: 40 passed, 6 warnings
```

**Key Test Coverage:**
- ✅ All 12 dashboard modules import successfully
- ✅ Data loaders and quality validation functional
- ✅ Metrics service calculates KPIs correctly
- ✅ UI patterns render HTML properly
- ✅ Decision intelligence generates recommendations
- ✅ Season deltas computed accurately

### 7.2 Full Test Suite

```bash
# All tests (214 valid tests, ~13s)
.venv\Scripts\python.exe -m pytest tests/ --ignore=tests/test_normalize_scorecard.py --ignore=tests/test_phase_shrinkage.py -v

# Expected: 214 passed, 34 skipped, 4 errors (opposition strength analysis - missing data file)
```

### 7.3 Known Test Exclusions

- `test_normalize_scorecard.py` — Placeholder, function not yet implemented
- `test_phase_shrinkage.py` — Placeholder, function not yet implemented
- `test_opposition_strength_analysis.py` — 4 tests ERROR (requires `data/normalized/matches_normalized.parquet`)

---

## 8. Troubleshooting

### 8.1 Import Errors

**Symptom:** `ImportError: cannot import name 'X' from 'Y'`

**Solution:**
```bash
# Verify virtual environment is activated
.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt

# Run smoke test
.venv\Scripts\python.exe -m pytest tests/test_smoke_dashboard.py::test_imports -v
```

### 8.2 Data Quality Errors

**Symptom:** Dashboard shows "Critical" status or refuses to load

**Solution:**
```bash
# Check data quality report
python -c "
from src.dashboard.services.data_quality import validate_match_records
from src.dashboard.services.data_source import load_match_records
df = load_match_records()
report = validate_match_records(df)
for finding in report['findings']:
    print(f\"{finding['severity']}: {finding['message']} - {finding['details']}\")
"

# Fix data issues in source parquet file, then restart dashboard
```

### 8.3 Performance Issues

**Symptom:** Dashboard loads slowly or times out

**Solutions:**
1. Clear Streamlit cache: Delete `.streamlit` folder in project root
2. Reduce data volume: Filter `matches.parquet` to most recent 2 seasons
3. Enable caching: Verify `@st.cache_data` decorators present in data loaders

### 8.4 Port Already in Use

**Symptom:** `OSError: [Errno 48] Address already in use`

**Solution:**
```bash
# Kill process on port 8501
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Or use different port
streamlit run src/dashboard/app.py --server.port 8502
```

---

## 9. Maintenance Schedule

### Daily
- ✅ Monitor dashboard uptime (should be <2s load time)
- ✅ Check data quality score in Executive Overview

### Weekly
- ✅ Update match data after each Janakpur Bolts fixture
- ✅ Run integration test suite (40 tests)
- ✅ Review decision intelligence recommendations for coaching staff

### Monthly
- ✅ Run full test suite (214 tests)
- ✅ Audit KPI calculation formulas against ground truth
- ✅ Update competition weights if new tournaments added

### Pre-Season
- ✅ Archive previous season data
- ✅ Update season labels in data files (S2 → S3)
- ✅ Refresh player roster CSV
- ✅ Recalibrate competition weights for new season

---

## 10. Change Log

### v1.0 (June 2, 2026) — Production Release

**Sprint Completion:**
- ✅ Day 1: Stabilization Baseline (import fixes, smoke tests)
- ✅ Day 2: Data Contract Layer (validation, quality reporting)
- ✅ Day 3: Shared Metrics Service (centralized KPI calculations)
- ✅ Day 4: UI Pattern Harmonization (reusable components)
- ✅ Day 5: Test & QA Layer (40 integration tests)
- ✅ Day 6: Decision Intelligence Pass (tactical recommendations)
- ✅ Day 7: Release & Playbook (this document)

**Test Results:**
- Integration Suite: 40/40 tests passing (100%)
- Full Suite: 214/218 valid tests passing (97.7%)
- Execution Time: <2s integration, <13s full

**Git Commits:**
- e702e51: Day 6 - Decision Intelligence Pass
- 6bb0c87: Day 5 - Test and QA Layer
- 503e53d: Day 4 - Team and Match Review Harmonization
- 96c8e34: Day 3 - Shared Metrics Service
- 0b1b7de: Day 2 - Data Contract Layer
- d8c2044: Day 1 - Stabilization Baseline

---

## 11. Support Contacts

**Technical Lead:** Analytics Team  
**Dashboard Issues:** Check test suite first, then review this runbook  
**Data Quality:** Run validation report (Section 5.1)  
**Feature Requests:** Log in project backlog

**Emergency Procedure:**
1. Check test suite: `.venv\Scripts\python.exe -m pytest tests/test_smoke_dashboard.py -v`
2. Review data quality score in dashboard
3. Check git log for recent changes: `git log --oneline -10`
4. Rollback if needed: `git checkout <previous_commit>`

---

**End of Operator Runbook**
