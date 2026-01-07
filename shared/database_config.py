"""Centralized Database Configuration for SaferTrade

Provides standardized database paths for all engines and a hardened
SQLite connection helper (WAL mode + busy timeout) to reduce the
"database is locked" errors seen under multi-process engine load.
Also includes PostgreSQL support for advanced analytics and cross-chain operations.

REAL DATA ONLY: This module does not fabricate data, it only returns
paths and connections to actual databases on disk.
"""

import os
import sqlite3
from typing import Optional

from shared.paths import DATABASES_DIR

# ============================================================================
# PRIMARY OPERATIONAL DATABASES
# ============================================================================

# Main detection database - All engine outputs
MAIN_DB = DATABASES_DIR / "safertrade.db"

# AI/RAG Intelligence System
KNOWLEDGE_DB = DATABASES_DIR / "knowledge.db"

# ML Arbitrage Forecasting
ARB_FORECAST_DB = DATABASES_DIR / "arb_forecast.db"

# Reddit Intelligence (API endpoint usage)
REDDIT_DB = DATABASES_DIR / "enhanced_reddit_intelligence.db"

# ============================================================================
# TEST DATABASES (for unit tests only)
# ============================================================================

TEST_DB = DATABASES_DIR.parent.parent / "tests" / "data" / "test.db"
TEST_ADDRESS_REPUTATION_DB = (
    DATABASES_DIR.parent.parent / "tests" / "data" / "test_address_reputation.db"
)
TEST_FLASH_LOAN_DB = (
    DATABASES_DIR.parent.parent / "tests" / "data" / "test_flash_loan.db"
)

# ============================================================================
# DATABASE CONNECTION HELPERS
# ============================================================================


def get_main_db_path() -> str:
    """Get path to main detection database as string"""
    return str(MAIN_DB)


def get_knowledge_db_path() -> str:
    """Get path to knowledge vault database as string"""
    return str(KNOWLEDGE_DB)


def get_arb_forecast_db_path() -> str:
    """Get path to arbitrage forecast database as string"""
    return str(ARB_FORECAST_DB)


def get_reddit_db_path() -> str:
    """Get path to Reddit intelligence database as string"""
    return str(REDDIT_DB)


# ============================================================================
# CONNECTION HELPERS (WAL + TIMEOUT)
# ============================================================================
def connect_main(timeout: float = 30.0, read_only: bool = False) -> sqlite3.Connection:
    """Return a configured connection to the main SQLite database.

    Applies WAL, NORMAL synchronous, and a busy timeout so writers queue
    briefly instead of failing immediately with 'database is locked'.

    Args:
        timeout: Busy timeout seconds (SQLite API expects float seconds for Python wrapper).
        read_only: If True, opens a read-only connection (shared cache) where supported.

    Returns:
        sqlite3.Connection ready for use.
    """
    uri = False
    db_path = get_main_db_path()
    if read_only:
        # Use URI mode for read-only if needed
        db_path = f"file:{db_path}?mode=ro"
        uri = True
    conn = sqlite3.connect(db_path, timeout=timeout, isolation_level=None, uri=uri)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        # Align busy timeout with the function parameter (seconds -> ms)
        conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)};")
        # Conservative cache/spill tuning
        conn.execute("PRAGMA temp_store=MEMORY;")
    except Exception:
        # PRAGMA failures are non-fatal; continue with connection
        pass
    return conn


def connect_db(
    db_path: str, timeout: float = 30.0, read_only: bool = False
) -> sqlite3.Connection:
    """Generic connection helper applying same PRAGMAs as connect_main.

    Engines with their own db_path should use this instead of raw sqlite3.connect.
    """
    uri = False
    original = db_path
    if read_only:
        db_path = f"file:{db_path}?mode=ro"
        uri = True
    conn = sqlite3.connect(db_path, timeout=timeout, isolation_level=None, uri=uri)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)};")
        conn.execute("PRAGMA temp_store=MEMORY;")
    except Exception:
        pass
    return conn


def is_postgres_enabled() -> bool:
    """Check if PostgreSQL is enabled via environment variable"""
    return os.getenv("USE_POSTGRES", "0").lower() in ("1", "true", "yes")


def get_primary_db_connection(timeout: float = 30.0, read_only: bool = False):
    """Get primary database connection (SQLite by default, PostgreSQL if enabled)"""
    if is_postgres_enabled():
        # Use PostgreSQL as primary database
        from .postgres_config import get_postgres_connection

        return get_postgres_connection()
    else:
        # Use SQLite as primary database
        return connect_main(timeout, read_only)


def execute_query(query: str, params=None, use_postgres: bool = None):
    """Execute a query using the appropriate database (primary by default)"""
    # Use the unified database interface from shared module to avoid circular imports
    from shared.database_interface import get_db_interface

    db_interface = get_db_interface()
    return db_interface.execute_query(query, params)


# ============================================================================
# DEPRECATED PATHS (for migration tracking)
# ============================================================================
# These paths are NO LONGER USED but documented for reference:
# - /path/to/safertrade/data/databases/safertrade.db (hardcoded - BAD)
# - ROOT_DIR / "shared" / "safertrade.db" (symlink - CONFUSING)
# - ROOT_DIR / "data" / "safertrade.db" (old location)
#
# ALL engines should now use: from shared.database_config import MAIN_DB
# ============================================================================
