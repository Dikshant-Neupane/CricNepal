FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default external data location inside the container.
# Mount your host folder containing parquet/rosters here:
#   -v D:/cric_data:/external/cric_data
ENV CRIC_DATA_DIR=/external/cric_data

# Create non-root user
RUN useradd -m -u 1000 bolts && chown -R bolts:bolts /app
USER bolts

# If normalized parquet doesn't exist yet, build it from CRIC_DATA_DIR by running the core pipeline.
# This makes the container self-contained for first-time startup.
CMD ["sh", "-c", "python -c \"from pathlib import Path; import os; p=Path(os.environ.get('CRICNEPAL_ROOT', '.'))/ 'data' / 'normalized' / 'matches_normalized.parquet'; import sys; sys.exit(0 if p.exists() else 1)\" || python refresh_all.py; python -m src.main"]
