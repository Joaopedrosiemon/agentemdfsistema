"""CSV/Excel import pipeline into SQLite."""

import pandas as pd
from typing import IO
from dataclasses import dataclass

from src.database.connection import get_connection
from src.database.queries import log_import, get_product_by_code
from src.utils.text_processing import normalize_column_name
from src.utils.validators import (
    validate_product_dataframe,
    validate_stock_dataframe,
    validate_equivalence_dataframe,
    validate_tape_dataframe,
)
from config.settings import (
    PRODUCT_COLUMN_MAP,
    STOCK_COLUMN_MAP,
    EQUIVALENCE_COLUMN_MAP,
    TAPE_COLUMN_MAP,
)


@dataclass
class ImportResult:
    success: bool
    rows_imported: int = 0
    rows_failed: int = 0
    errors: list[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


def _read_file(file: IO, file_name: str) -> pd.DataFrame:
    """Read CSV or Excel file into DataFrame."""
    if file_name.endswith(".csv"):
        return pd.read_csv(file, encoding="utf-8-sig")
    elif file_name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    else:
        raise ValueError(f"Tipo de arquivo nao suportado: {file_name}")


def _map_columns(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    """Map column names from Portuguese/variant to standardized English names."""
    rename_map = {}
    for col in df.columns:
        normalized = normalize_column_name(col)
        if normalized in column_map:
            rename_map[col] = column_map[normalized]
    return df.rename(columns=rename_map)


def import_products(file: IO, file_name: str) -> ImportResult:
    """Import MDF product data from CSV/Excel."""
    try:
        df = _read_file(file, file_name)
        df = _map_columns(df, PRODUCT_COLUMN_MAP)

        validation = validate_product_dataframe(df)
        if not validation.is_valid:
            log_import(file_name, "products", 0, 0, "failed", "; ".join(validation.errors))
            return ImportResult(False, errors=validation.errors, warnings=validation.warnings)

        conn = get_connection()
        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO products
                       (brand, product_name, product_code, thickness_mm, finish,
                        width_mm, height_mm, color_family, category, image_path,
                        updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (
                        str(row["brand"]).strip(),
                        str(row["product_name"]).strip(),
                        str(row["product_code"]).strip(),
                        float(row["thickness_mm"]) if pd.notna(row.get("thickness_mm")) else None,
                        str(row["finish"]).strip() if pd.notna(row.get("finish")) else None,
                        float(row["width_mm"]) if pd.notna(row.get("width_mm")) else None,
                        float(row["height_mm"]) if pd.notna(row.get("height_mm")) else None,
                        str(row["color_family"]).strip() if pd.notna(row.get("color_family")) else None,
                        str(row["category"]).strip() if pd.notna(row.get("category")) else None,
                        str(row["image_path"]).strip() if pd.notna(row.get("image_path")) else None,
                    ),
                )
                imported += 1
            except Exception:
                failed += 1

        conn.commit()
        status = "success" if failed == 0 else "partial"
        log_import(file_name, "products", imported, failed, status)
        return ImportResult(True, imported, failed, warnings=validation.warnings)

    except Exception as e:
        log_import(file_name, "products", 0, 0, "failed", str(e))
        return ImportResult(False, errors=[str(e)])


def import_stock(file: IO, file_name: str) -> ImportResult:
    """Import stock data from CSV/Excel."""
    try:
        df = _read_file(file, file_name)
        df = _map_columns(df, STOCK_COLUMN_MAP)

        validation = validate_stock_dataframe(df)
        if not validation.is_valid:
            log_import(file_name, "stock", 0, 0, "failed", "; ".join(validation.errors))
            return ImportResult(False, errors=validation.errors, warnings=validation.warnings)

        conn = get_connection()
        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                code = str(row["product_code"]).strip()
                product = get_product_by_code(code)
                if not product:
                    failed += 1
                    continue

                conn.execute(
                    """INSERT OR REPLACE INTO stock
                       (product_id, quantity_available, quantity_reserved,
                        minimum_stock, location, unit, last_updated)
                       VALUES (?, ?, ?, ?, ?, ?,  CURRENT_TIMESTAMP)""",
                    (
                        product["id"],
                        float(row["quantity_available"]) if pd.notna(row.get("quantity_available")) else 0,
                        float(row.get("quantity_reserved", 0)) if pd.notna(row.get("quantity_reserved")) else 0,
                        float(row.get("minimum_stock", 0)) if pd.notna(row.get("minimum_stock")) else 0,
                        str(row.get("location", "principal")).strip() if pd.notna(row.get("location")) else "principal",
                        str(row.get("unit", "chapa")).strip() if pd.notna(row.get("unit")) else "chapa",
                    ),
                )
                imported += 1
            except Exception:
                failed += 1

        conn.commit()
        status = "success" if failed == 0 else "partial"
        log_import(file_name, "stock", imported, failed, status)
        return ImportResult(True, imported, failed, warnings=validation.warnings)

    except Exception as e:
        log_import(file_name, "stock", 0, 0, "failed", str(e))
        return ImportResult(False, errors=[str(e)])


def import_equivalences(file: IO, file_name: str) -> ImportResult:
    """Import direct equivalence mappings from CSV/Excel."""
    try:
        df = _read_file(file, file_name)
        df = _map_columns(df, EQUIVALENCE_COLUMN_MAP)

        validation = validate_equivalence_dataframe(df)
        if not validation.is_valid:
            log_import(file_name, "equivalences", 0, 0, "failed", "; ".join(validation.errors))
            return ImportResult(False, errors=validation.errors, warnings=validation.warnings)

        conn = get_connection()
        imported = 0
        failed = 0

        has_codes = "code_a" in df.columns and "code_b" in df.columns

        for _, row in df.iterrows():
            try:
                if has_codes:
                    product_a = get_product_by_code(str(row["code_a"]).strip())
                    product_b = get_product_by_code(str(row["code_b"]).strip())
                else:
                    # Find by name + brand
                    name_a = str(row["product_name_a"]).strip()
                    brand_a = str(row["brand_a"]).strip()
                    name_b = str(row["product_name_b"]).strip()
                    brand_b = str(row["brand_b"]).strip()

                    product_a = conn.execute(
                        "SELECT * FROM products WHERE product_name = ? AND brand = ? AND is_active = 1",
                        (name_a, brand_a),
                    ).fetchone()
                    product_b = conn.execute(
                        "SELECT * FROM products WHERE product_name = ? AND brand = ? AND is_active = 1",
                        (name_b, brand_b),
                    ).fetchone()

                if not product_a or not product_b:
                    failed += 1
                    continue

                # Ensure consistent ordering (lower id first)
                id_a = min(product_a["id"], product_b["id"])
                id_b = max(product_a["id"], product_b["id"])

                source = str(row.get("equivalence_source", "")).strip() if pd.notna(row.get("equivalence_source")) else None
                confidence = float(row.get("confidence", 1.0)) if pd.notna(row.get("confidence")) else 1.0

                conn.execute(
                    """INSERT OR IGNORE INTO direct_equivalences
                       (product_id_a, product_id_b, equivalence_source, confidence)
                       VALUES (?, ?, ?, ?)""",
                    (id_a, id_b, source, confidence),
                )
                imported += 1
            except Exception:
                failed += 1

        conn.commit()
        status = "success" if failed == 0 else "partial"
        log_import(file_name, "equivalences", imported, failed, status)
        return ImportResult(True, imported, failed, warnings=validation.warnings)

    except Exception as e:
        log_import(file_name, "equivalences", 0, 0, "failed", str(e))
        return ImportResult(False, errors=[str(e)])


def import_edging_tapes(file: IO, file_name: str) -> ImportResult:
    """Import edging tape data from CSV/Excel."""
    try:
        df = _read_file(file, file_name)
        df = _map_columns(df, TAPE_COLUMN_MAP)

        validation = validate_tape_dataframe(df)
        if not validation.is_valid:
            log_import(file_name, "tapes", 0, 0, "failed", "; ".join(validation.errors))
            return ImportResult(False, errors=validation.errors, warnings=validation.warnings)

        conn = get_connection()
        imported = 0
        failed = 0

        for _, row in df.iterrows():
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO edging_tapes
                       (brand, tape_name, tape_code, width_mm, thickness_mm,
                        finish, color_family)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(row["brand"]).strip(),
                        str(row["tape_name"]).strip(),
                        str(row["tape_code"]).strip(),
                        float(row["width_mm"]) if pd.notna(row.get("width_mm")) else None,
                        float(row["thickness_mm"]) if pd.notna(row.get("thickness_mm")) else None,
                        str(row["finish"]).strip() if pd.notna(row.get("finish")) else None,
                        str(row["color_family"]).strip() if pd.notna(row.get("color_family")) else None,
                    ),
                )
                imported += 1
            except Exception:
                failed += 1

        conn.commit()
        status = "success" if failed == 0 else "partial"
        log_import(file_name, "tapes", imported, failed, status)
        return ImportResult(True, imported, failed, warnings=validation.warnings)

    except Exception as e:
        log_import(file_name, "tapes", 0, 0, "failed", str(e))
        return ImportResult(False, errors=[str(e)])
