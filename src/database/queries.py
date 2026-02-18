"""Parameterized query functions for database operations."""

import sqlite3
from typing import Optional
from src.database.connection import get_connection


# ── Products ──────────────────────────────────────────────

def get_product_by_id(product_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,)
    ).fetchone()


def get_product_by_code(product_code: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM products WHERE product_code = ? AND is_active = 1",
        (product_code,),
    ).fetchone()


def search_products_by_name(query: str, limit: int = 10) -> list[sqlite3.Row]:
    conn = get_connection()
    pattern = f"%{query}%"
    return conn.execute(
        """SELECT * FROM products
           WHERE (product_name LIKE ? OR brand LIKE ? OR product_code LIKE ?)
           AND is_active = 1
           LIMIT ?""",
        (pattern, pattern, pattern, limit),
    ).fetchall()


def get_all_active_products() -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM products WHERE is_active = 1"
    ).fetchall()


def get_products_by_category(category: str) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM products WHERE category = ? AND is_active = 1",
        (category,),
    ).fetchall()


def count_products() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM products WHERE is_active = 1").fetchone()
    return row["cnt"] if row else 0


# ── Stock ─────────────────────────────────────────────────

def get_stock_by_product_id(product_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM stock WHERE product_id = ?", (product_id,)
    ).fetchone()


def get_product_with_stock(product_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """SELECT p.*, s.quantity_available, s.quantity_reserved,
                  s.minimum_stock, s.location, s.unit, s.last_updated as stock_updated
           FROM products p
           LEFT JOIN stock s ON p.id = s.product_id
           WHERE p.id = ? AND p.is_active = 1""",
        (product_id,),
    ).fetchone()


def get_products_in_stock(min_qty: float = 1.0) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """SELECT p.*, s.quantity_available, s.quantity_reserved, s.location
           FROM products p
           JOIN stock s ON p.id = s.product_id
           WHERE p.is_active = 1
           AND (s.quantity_available - s.quantity_reserved) >= ?""",
        (min_qty,),
    ).fetchall()


def count_stock_entries() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM stock").fetchone()
    return row["cnt"] if row else 0


# ── Direct Equivalences ──────────────────────────────────

def get_equivalents(product_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """SELECT p.*, de.equivalence_source, de.confidence, de.notes,
                  s.quantity_available, s.quantity_reserved, s.location
           FROM direct_equivalences de
           JOIN products p ON (
               CASE WHEN de.product_id_a = ? THEN de.product_id_b
                    ELSE de.product_id_a END = p.id
           )
           LEFT JOIN stock s ON p.id = s.product_id
           WHERE (de.product_id_a = ? OR de.product_id_b = ?)
           AND p.is_active = 1""",
        (product_id, product_id, product_id),
    ).fetchall()


def count_equivalences() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM direct_equivalences").fetchone()
    return row["cnt"] if row else 0


# ── Edging Tapes ─────────────────────────────────────────

def get_compatible_tapes(product_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """SELECT et.*, tpc.compatibility_type
           FROM tape_product_compatibility tpc
           JOIN edging_tapes et ON tpc.tape_id = et.id
           WHERE tpc.product_id = ? AND et.is_active = 1
           ORDER BY
               CASE tpc.compatibility_type
                   WHEN 'official' THEN 1
                   WHEN 'recommended' THEN 2
                   WHEN 'alternative' THEN 3
               END""",
        (product_id,),
    ).fetchall()


def get_tape_equivalents(tape_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """SELECT et.*
           FROM tape_equivalences te
           JOIN edging_tapes et ON (
               CASE WHEN te.tape_id_a = ? THEN te.tape_id_b
                    ELSE te.tape_id_a END = et.id
           )
           WHERE (te.tape_id_a = ? OR te.tape_id_b = ?)
           AND et.is_active = 1""",
        (tape_id, tape_id, tape_id),
    ).fetchall()


def get_tapes_by_color_family(color_family: str) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM edging_tapes WHERE color_family = ? AND is_active = 1",
        (color_family,),
    ).fetchall()


def count_tapes() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM edging_tapes WHERE is_active = 1").fetchone()
    return row["cnt"] if row else 0


# ── Similarity Cache ─────────────────────────────────────

def get_cached_similarity(product_id_a: int, product_id_b: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """SELECT * FROM similarity_cache
           WHERE (product_id_a = ? AND product_id_b = ?)
              OR (product_id_a = ? AND product_id_b = ?)""",
        (product_id_a, product_id_b, product_id_b, product_id_a),
    ).fetchone()


def get_cached_similarities_for_product(product_id: int, min_score: float = 0.5) -> list[sqlite3.Row]:
    conn = get_connection()
    return conn.execute(
        """SELECT sc.*, p.*,
                  s.quantity_available, s.quantity_reserved, s.location
           FROM similarity_cache sc
           JOIN products p ON (
               CASE WHEN sc.product_id_a = ? THEN sc.product_id_b
                    ELSE sc.product_id_a END = p.id
           )
           LEFT JOIN stock s ON p.id = s.product_id
           WHERE (sc.product_id_a = ? OR sc.product_id_b = ?)
           AND sc.similarity_score >= ?
           AND p.is_active = 1
           ORDER BY sc.similarity_score DESC""",
        (product_id, product_id, product_id, min_score),
    ).fetchall()


def save_similarity_cache(
    product_id_a: int, product_id_b: int, score: float, justification: str
):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO similarity_cache
           (product_id_a, product_id_b, similarity_score, justification)
           VALUES (?, ?, ?, ?)""",
        (product_id_a, product_id_b, score, justification),
    )
    conn.commit()


# ── Feedback ─────────────────────────────────────────────

def save_feedback(
    session_id: str,
    original_product_id: int,
    suggested_product_id: int,
    suggestion_type: str,
    accepted: bool,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO feedback
           (session_id, original_product_id, suggested_product_id,
            suggestion_type, accepted, rating, comment)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session_id, original_product_id, suggested_product_id,
         suggestion_type, accepted, rating, comment),
    )
    conn.commit()
    return cursor.lastrowid


def get_feedback_stats() -> dict:
    conn = get_connection()
    row = conn.execute(
        """SELECT
               COUNT(*) as total,
               SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) as accepted,
               SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END) as rejected,
               AVG(CASE WHEN rating IS NOT NULL THEN rating END) as avg_rating
           FROM feedback"""
    ).fetchone()
    if not row or row["total"] == 0:
        return {"total": 0, "accepted": 0, "rejected": 0, "acceptance_rate": 0, "avg_rating": None}
    return {
        "total": row["total"],
        "accepted": row["accepted"] or 0,
        "rejected": row["rejected"] or 0,
        "acceptance_rate": (row["accepted"] or 0) / row["total"] if row["total"] > 0 else 0,
        "avg_rating": round(row["avg_rating"], 1) if row["avg_rating"] else None,
    }


# ── Import Log ───────────────────────────────────────────

def log_import(file_name: str, file_type: str, rows_imported: int,
               rows_failed: int, status: str, error_message: str = None) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO import_log
           (file_name, file_type, rows_imported, rows_failed, status, error_message)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (file_name, file_type, rows_imported, rows_failed, status, error_message),
    )
    conn.commit()
    return cursor.lastrowid
