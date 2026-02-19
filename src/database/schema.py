"""Database schema definition and initialization."""

from src.database.connection import get_connection

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        product_name TEXT NOT NULL,
        product_code TEXT NOT NULL UNIQUE,
        thickness_mm REAL,
        finish TEXT,
        width_mm REAL,
        height_mm REAL,
        color_family TEXT,
        category TEXT,
        image_path TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        location TEXT DEFAULT 'principal',
        quantity_available REAL NOT NULL DEFAULT 0,
        quantity_reserved REAL NOT NULL DEFAULT 0,
        minimum_stock REAL DEFAULT 0,
        unit TEXT DEFAULT 'chapa',
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS direct_equivalences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id_a INTEGER NOT NULL,
        product_id_b INTEGER NOT NULL,
        equivalence_source TEXT,
        confidence REAL DEFAULT 1.0,
        notes TEXT,
        FOREIGN KEY (product_id_a) REFERENCES products(id),
        FOREIGN KEY (product_id_b) REFERENCES products(id),
        UNIQUE(product_id_a, product_id_b)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS edging_tapes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        tape_name TEXT NOT NULL,
        tape_code TEXT NOT NULL UNIQUE,
        width_mm REAL,
        thickness_mm REAL,
        finish TEXT,
        color_family TEXT,
        quantity_available REAL DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tape_product_compatibility (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tape_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        compatibility_type TEXT DEFAULT 'official',
        FOREIGN KEY (tape_id) REFERENCES edging_tapes(id),
        FOREIGN KEY (product_id) REFERENCES products(id),
        UNIQUE(tape_id, product_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tape_equivalences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tape_id_a INTEGER NOT NULL,
        tape_id_b INTEGER NOT NULL,
        FOREIGN KEY (tape_id_a) REFERENCES edging_tapes(id),
        FOREIGN KEY (tape_id_b) REFERENCES edging_tapes(id),
        UNIQUE(tape_id_a, tape_id_b)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS similarity_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id_a INTEGER NOT NULL,
        product_id_b INTEGER NOT NULL,
        similarity_score REAL NOT NULL,
        justification TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id_a) REFERENCES products(id),
        FOREIGN KEY (product_id_b) REFERENCES products(id),
        UNIQUE(product_id_a, product_id_b)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        original_product_id INTEGER,
        suggested_product_id INTEGER,
        suggestion_type TEXT,
        rating INTEGER CHECK(rating BETWEEN 1 AND 5),
        accepted BOOLEAN,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (original_product_id) REFERENCES products(id),
        FOREIGN KEY (suggested_product_id) REFERENCES products(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS import_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        file_type TEXT,
        rows_imported INTEGER DEFAULT 0,
        rows_failed INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        error_message TEXT,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand)",
    "CREATE INDEX IF NOT EXISTS idx_products_code ON products(product_code)",
    "CREATE INDEX IF NOT EXISTS idx_products_name ON products(product_name)",
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)",
    "CREATE INDEX IF NOT EXISTS idx_stock_product ON stock(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_stock_product_location ON stock(product_id, location)",
    "CREATE INDEX IF NOT EXISTS idx_equivalences_a ON direct_equivalences(product_id_a)",
    "CREATE INDEX IF NOT EXISTS idx_equivalences_b ON direct_equivalences(product_id_b)",
    "CREATE INDEX IF NOT EXISTS idx_tape_compat_product ON tape_product_compatibility(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_tape_compat_tape ON tape_product_compatibility(tape_id)",
    "CREATE INDEX IF NOT EXISTS idx_similarity_a ON similarity_cache(product_id_a)",
    "CREATE INDEX IF NOT EXISTS idx_similarity_b ON similarity_cache(product_id_b)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_original ON feedback(original_product_id)",
]


def initialize_database():
    """Create all tables and indexes."""
    conn = get_connection()
    cursor = conn.cursor()
    for table_sql in TABLES:
        cursor.execute(table_sql)
    for index_sql in INDEXES:
        cursor.execute(index_sql)
    _ensure_column(conn, "edging_tapes", "quantity_available", "REAL DEFAULT 0")
    conn.commit()


def _ensure_column(conn, table: str, column: str, ddl: str):
    """Add column if missing (lightweight migration)."""
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row["name"] for row in cols}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
