import sqlite3
from pathlib import Path
from config.settings import DB_PATH


_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """Get or create a singleton SQLite connection."""
    global _connection
    if _connection is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(
            str(DB_PATH),
            check_same_thread=False,
            timeout=30,
        )
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        _connection.execute("PRAGMA busy_timeout=30000")
    return _connection


def close_connection():
    """Close the singleton connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
