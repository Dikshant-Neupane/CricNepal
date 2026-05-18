"""
NPL Data Ingestion Package
===========================
Scripts for ingesting NPL cricket data from Parquet files into PostgreSQL.

Modules:
  - run_migrations: Apply database schema migrations
  - ingest_npl_parquet: Load NPL data from scraping pipeline
"""

__version__ = "1.0.0"

__all__ = [
    "run_migrations",
    "ingest_npl_parquet",
]
