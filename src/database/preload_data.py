"""Pre-load bundled data (similarity + stock spreadsheets) into the database.

This module reads the Grupo Locatelli similarity table and stock spreadsheet,
automatically creating products + equivalences + stock entries so all users
have the data on first access.
"""

import re
import unicodedata

import pandas as pd
from pathlib import Path

from src.database.connection import get_connection
from src.database.queries import log_import

from config.settings import DATA_DIR

BUNDLED_DIR = DATA_DIR / "bundled"
SIMILARITY_FILE = BUNDLED_DIR / "TABELA_SIMILARIDADE_GRUPO_LOCATELLI_0209.xlsx"
STOCK_FILE = BUNDLED_DIR / "estoque_atual.xlsx"

# The 7 manufacturers in column order (row index 1 of the spreadsheet)
MANUFACTURERS = [
    "DURATEX",
    "ARAUCO",
    "GUARARAPES",
    "EUCATEX",
    "PLACAS DO BRASIL",
    "FLORAPLAC",
    "BERNECK",
]


def is_data_preloaded() -> bool:
    """Check if bundled data was already imported."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM import_log WHERE file_name = ? AND status = 'success'",
        ("PRELOAD_SIMILARITY_TABLE",),
    ).fetchone()
    return (row["cnt"] or 0) > 0


def preload_similarity_table() -> dict:
    """
    Read the Grupo Locatelli similarity spreadsheet and import:
    1. Products — one entry per unique (brand, product_name)
    2. Direct equivalences — every pair of products on the same row

    The spreadsheet has:
    - Row 0: Headers (FABRICANTE, Coluna1, ...) — ignored
    - Row 1: Manufacturer names (DURATEX, ARAUCO, ...)
    - Rows 2+: Product names per manufacturer

    Returns dict with import stats.
    """
    if not SIMILARITY_FILE.exists():
        return {
            "success": False,
            "error": f"Arquivo nao encontrado: {SIMILARITY_FILE}",
        }

    if is_data_preloaded():
        return {"success": True, "message": "Dados ja carregados anteriormente."}

    try:
        # Read without headers — we'll parse manually
        df = pd.read_excel(SIMILARITY_FILE, header=None)

        # Row 1 has the manufacturer names, data starts at row 2
        # Columns: 0=unused, 1=DURATEX, 2=ARAUCO, 3=GUARARAPES, 4=EUCATEX,
        #          5=PLACAS DO BRASIL, 6=FLORAPLAC, 7=BERNECK
        manufacturer_cols = {}
        for col_idx, brand in enumerate(MANUFACTURERS):
            manufacturer_cols[col_idx + 1] = brand

        conn = get_connection()
        products_created = 0
        equivalences_created = 0
        errors = []

        # Process each data row (starting from row 3)
        # Row 0 = empty, Row 1 = headers, Row 2 = manufacturer names, Row 3+ = data
        for row_idx in range(3, len(df)):
            row = df.iloc[row_idx]

            # Collect valid products on this row
            row_products = []  # list of (brand, product_name)
            for col_idx, brand in manufacturer_cols.items():
                cell_value = row.iloc[col_idx] if col_idx < len(row) else None
                if pd.notna(cell_value) and str(cell_value).strip():
                    product_name = str(cell_value).strip()
                    row_products.append((brand, product_name))

            # Insert products into the database
            product_ids = []  # list of (product_id, brand, product_name)
            for brand, product_name in row_products:
                product_id = _ensure_product(conn, brand, product_name)
                if product_id:
                    product_ids.append(product_id)
                    products_created += 1

            # Create equivalence pairs for all combinations on this row
            for i in range(len(product_ids)):
                for j in range(i + 1, len(product_ids)):
                    id_a = min(product_ids[i], product_ids[j])
                    id_b = max(product_ids[i], product_ids[j])
                    try:
                        conn.execute(
                            """INSERT OR IGNORE INTO direct_equivalences
                               (product_id_a, product_id_b, equivalence_source, confidence)
                               VALUES (?, ?, ?, ?)""",
                            (id_a, id_b, "Tabela Similaridade Grupo Locatelli", 1.0),
                        )
                        equivalences_created += 1
                    except Exception as e:
                        errors.append(f"Equivalence {id_a}-{id_b}: {str(e)}")

        conn.commit()

        # Log the import
        log_import(
            "PRELOAD_SIMILARITY_TABLE",
            "preload",
            products_created,
            len(errors),
            "success" if not errors else "partial",
            "; ".join(errors[:5]) if errors else None,
        )

        return {
            "success": True,
            "products_created": products_created,
            "equivalences_created": equivalences_created,
            "errors": errors,
        }

    except Exception as e:
        log_import("PRELOAD_SIMILARITY_TABLE", "preload", 0, 0, "failed", str(e))
        return {"success": False, "error": str(e)}


def _ensure_product(conn, brand: str, product_name: str) -> int | None:
    """
    Ensure a product exists in the database. If it already exists, return its ID.
    If not, create it and return the new ID.

    Uses brand + product_name as the unique identifier.
    product_code is auto-generated as BRAND_PRODUCTNAME (normalized).
    """
    # Generate a deterministic product_code
    product_code = _generate_product_code(brand, product_name)

    # Check if already exists
    existing = conn.execute(
        "SELECT id FROM products WHERE product_code = ?",
        (product_code,),
    ).fetchone()

    if existing:
        return existing["id"]

    # Create new product
    try:
        cursor = conn.execute(
            """INSERT INTO products
               (brand, product_name, product_code, category, is_active)
               VALUES (?, ?, ?, ?, 1)""",
            (brand, product_name, product_code, _infer_category(product_name)),
        )
        return cursor.lastrowid
    except Exception:
        return None


def _generate_product_code(brand: str, product_name: str) -> str:
    """Generate a unique product code from brand + name."""
    # Normalize: uppercase, remove special chars, replace spaces with underscore
    brand_part = brand.upper().replace(" ", "").replace("/", "")[:6]
    name_part = (
        product_name.upper()
        .replace(" ", "_")
        .replace("/", "_")
        .replace(".", "")
        .replace(",", "")
    )
    return f"{brand_part}_{name_part}"


def _infer_category(product_name: str) -> str:
    """Try to infer the MDF category from the product name."""
    name_upper = product_name.upper()

    # White/solid colors
    unicolor_words = [
        "BRANCO", "PRETO", "CINZA", "TITANIO", "GRAFITE", "GRAFITO",
        "AREIA", "BEIGE", "CREME", "MARFIM", "NEVE",
    ]
    if any(w in name_upper for w in unicolor_words):
        return "unicolor"

    # Wood patterns
    madeirado_words = [
        "CARVALHO", "NOGAL", "IMBUIA", "CEDAR", "CEDRO", "TECA", "TEKA",
        "IPANEMA", "ITAPUA", "CANELA", "CASTANHO", "AMENDOA", "AMÊNDOA",
        "FREIJO", "AMEIXA", "NOGUEIRA", "AVELA", "AVELÃ", "RUSTICO",
        "ROVERE", "MONTANA", "HANOVER", "MELBOURNE", "DAMASCO",
        "ACACIA", "SAVANA", "JATOBA", "JEQUITIBA", "LOURO",
        "GENGIBRE", "LENHO", "PECAN", "CASTANHEIRA",
        "AMENDOEIRA", "LAMINA", "NATURAL", "TREND",
        "MADEIRA", "PINHO", "MAPLE", "OAK", "WALNUT",
    ]
    if any(w in name_upper for w in madeirado_words):
        return "madeirado"

    # Fantasy/textured
    fantasia_words = [
        "TRAMA", "ESSENCIAL", "SILK", "LINHO", "CONCRETO", "BETON",
        "CHESS", "CONNECT", "DIAMANTE", "SAGRADO", "DUNAS",
        "FUME", "POENTE", "LUAR", "GIANDUIA", "CACAO",
    ]
    if any(w in name_upper for w in fantasia_words):
        return "fantasia"

    return "outro"


# ── Stock Preload ─────────────────────────────────────────────

def is_stock_preloaded() -> bool:
    """Check if stock data was already imported."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM import_log WHERE file_name = ? AND status IN ('success', 'partial')",
        ("PRELOAD_STOCK",),
    ).fetchone()
    return (row["cnt"] or 0) > 0


def preload_stock() -> dict:
    """
    Read the Grupo Locatelli stock spreadsheet and import:
    1. Products from "Chapas" section → MDF products (with stock)
    2. Products from "Fitas E Acabamentos" → edging tapes (with stock-like info)

    Also tries to match stock products with existing products from the
    similarity table using fuzzy name matching.

    The spreadsheet columns:
    - Codigo do Produto (product code from ERP)
    - Produto (full product name like "Mdf Duratex Carvalho Hanover Design 15mm 2f")
    - Secao ("Chapas" or "Fitas E Acabamentos")
    - Marca (brand)
    - Saldo (stock quantity)
    - Preco Venda (selling price)
    """
    if not STOCK_FILE.exists():
        return {
            "success": False,
            "error": f"Arquivo de estoque nao encontrado: {STOCK_FILE}",
        }

    if is_stock_preloaded():
        return {"success": True, "message": "Estoque ja carregado anteriormente."}

    try:
        df = pd.read_excel(STOCK_FILE)

        # Normalize column names (handle encoding issues with accents)
        df.columns = [_normalize_col_name(c) for c in df.columns]

        # Identify columns
        col_code = _find_column(df, ["codigo do produto", "codigo", "code"])
        col_name = _find_column(df, ["produto", "product", "nome"])
        col_section = _find_column(df, ["secao", "section"])
        col_brand = _find_column(df, ["marca", "brand"])
        col_stock = _find_column(df, ["saldo", "estoque", "stock", "quantidade"])
        col_price = _find_column(df, ["preco venda", "preco", "price"])

        if not col_name or not col_brand or not col_stock:
            return {
                "success": False,
                "error": "Colunas obrigatorias nao encontradas (Produto, Marca, Saldo).",
            }

        # Remove totals row (last row with NaN in product name)
        df = df.dropna(subset=[col_name])

        conn = get_connection()
        products_created = 0
        products_updated = 0
        stock_entries = 0
        tapes_created = 0
        errors = []

        for _, row in df.iterrows():
            try:
                product_name = str(row[col_name]).strip()
                brand = str(row[col_brand]).strip().upper()
                stock_qty = float(row[col_stock]) if pd.notna(row[col_stock]) else 0
                erp_code = str(int(row[col_code])) if pd.notna(row.get(col_code)) else ""
                section = str(row[col_section]).strip() if col_section and pd.notna(row.get(col_section)) else ""
                price = float(row[col_price]) if col_price and pd.notna(row.get(col_price)) else None

                # Parse product details from full name
                parsed = _parse_product_name(product_name, brand)

                if "fita" in section.lower() or "acabamento" in section.lower():
                    # Import as edging tape
                    tape_id = _import_tape(conn, parsed, brand, erp_code, stock_qty)
                    if tape_id:
                        tapes_created += 1
                else:
                    # Import as MDF product (Chapas)
                    # Try to match with existing product from similarity table
                    existing_id = _match_existing_product(conn, parsed, brand)

                    if existing_id:
                        # Update existing product with stock info and additional details
                        _update_product_details(conn, existing_id, parsed, erp_code, price)
                        _upsert_stock(conn, existing_id, stock_qty)
                        products_updated += 1
                        stock_entries += 1
                    else:
                        # Create new product + stock
                        product_id = _create_stock_product(conn, parsed, brand, erp_code, price)
                        if product_id:
                            _upsert_stock(conn, product_id, stock_qty)
                            products_created += 1
                            stock_entries += 1

            except Exception as e:
                errors.append(f"{product_name}: {str(e)}")

        conn.commit()

        status = "success" if not errors else "partial"
        log_import(
            "PRELOAD_STOCK",
            "stock",
            stock_entries + tapes_created,
            len(errors),
            status,
            "; ".join(errors[:5]) if errors else None,
        )

        return {
            "success": True,
            "products_created": products_created,
            "products_updated": products_updated,
            "stock_entries": stock_entries,
            "tapes_created": tapes_created,
            "errors": errors[:10],
        }

    except Exception as e:
        log_import("PRELOAD_STOCK", "stock", 0, 0, "failed", str(e))
        return {"success": False, "error": str(e)}


def _normalize_col_name(name: str) -> str:
    """Normalize column name: remove accents, lowercase, strip."""
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", str(name))
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return without_accents.lower().strip()


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find the first matching column from a list of candidates."""
    # First pass: exact match
    for candidate in candidates:
        for col in df.columns:
            if col == candidate:
                return col

    # Second pass: column starts with candidate or candidate starts with column
    for candidate in candidates:
        for col in df.columns:
            if col.startswith(candidate) or candidate.startswith(col):
                return col

    return None


def _parse_product_name(full_name: str, brand: str) -> dict:
    """
    Parse a detailed product name like 'Mdf Duratex Carvalho Hanover Design 15mm 2f'
    into structured data.

    Returns dict with: short_name, thickness_mm, finish, faces, is_hydro, full_name
    """
    result = {
        "full_name": full_name,
        "short_name": "",
        "thickness_mm": None,
        "finish": None,
        "faces": None,
        "is_hydro": False,
    }

    name = full_name

    # Detect hydro/ultra
    if "hidro" in name.lower() or "ultra" in name.lower():
        result["is_hydro"] = True

    # Extract thickness (e.g., "15mm", "06mm")
    thickness_match = re.search(r'(\d+(?:[.,]\d+)?)\s*mm', name, re.IGNORECASE)
    if thickness_match:
        result["thickness_mm"] = float(thickness_match.group(1).replace(",", "."))

    # Extract faces (e.g., "2f", "1f")
    faces_match = re.search(r'(\d)\s*f\b', name, re.IGNORECASE)
    if faces_match:
        result["faces"] = int(faces_match.group(1))

    # Extract finish keywords
    finish_keywords = [
        "Design", "Silk", "Essencial", "Lacca", "Tx", "Matt",
        "Supermatte", "Acetinatta", "Jateado", "Nature", "Natura",
        "Pele", "Line", "Bold", "Chess", "Duna", "Trama",
        "Orvalho", "Soft", "Liso",
    ]
    found_finishes = []
    for keyword in finish_keywords:
        if keyword.lower() in name.lower():
            found_finishes.append(keyword)
    if found_finishes:
        result["finish"] = " ".join(found_finishes)

    # Build short name by removing common prefixes/suffixes
    short = name

    # Remove leading "Mdf", "Pvc", "Mdp", etc.
    short = re.sub(r'^(Mdf|Mdp|Pvc|Bp|Hdf|Eucadur|Ripado)\s+', '', short, flags=re.IGNORECASE)

    # Remove brand name
    brand_words = brand.upper().split()
    for bw in brand_words:
        short = re.sub(r'\b' + re.escape(bw) + r'\b', '', short, flags=re.IGNORECASE)

    # Remove thickness, faces, dimensions
    short = re.sub(r'\d+(?:[.,]\d+)?\s*mm', '', short)
    short = re.sub(r'\d+\s*f\b', '', short, flags=re.IGNORECASE)
    short = re.sub(r'\d+[x,]\d+(?:[x,]\d+)?', '', short)  # dimensions like 2,75x1,85

    # Remove parenthesized codes like (10088417)
    short = re.sub(r'\([^)]*\)', '', short)

    # Remove "Hidro/Ultra", "Avariado", "Cx \d+"
    short = re.sub(r'Hidro/?Ultra', '', short, flags=re.IGNORECASE)
    short = re.sub(r'Avariado', '', short, flags=re.IGNORECASE)
    short = re.sub(r'Cx\s*\d+', '', short, flags=re.IGNORECASE)

    # Remove finish keywords for matching (keep the raw core name)
    for keyword in finish_keywords:
        short = re.sub(r'\b' + re.escape(keyword) + r'\b', '', short, flags=re.IGNORECASE)

    # Clean up whitespace and dashes
    short = re.sub(r'\s*-\s*', ' ', short)
    short = re.sub(r'\s+', ' ', short).strip()

    result["short_name"] = short.upper()
    return result


def _match_existing_product(conn, parsed: dict, brand: str) -> int | None:
    """
    Try to match a stock product with an existing product from the similarity table.
    Uses the short_name extracted from the full product name.
    """
    short_name = parsed["short_name"]
    if not short_name:
        return None

    # Normalize brand for comparison
    brand_upper = brand.upper()
    brand_map = {
        "PLACAS DO BRASIL": "PLACAS DO BRASIL",
        "PLACAS": "PLACAS DO BRASIL",
    }
    brand_db = brand_map.get(brand_upper, brand_upper)

    # Strategy 1: Exact match on brand + product_name
    existing = conn.execute(
        "SELECT id FROM products WHERE brand = ? AND UPPER(product_name) = ? AND is_active = 1",
        (brand_db, short_name),
    ).fetchone()
    if existing:
        return existing["id"]

    # Strategy 2: Check if the short_name CONTAINS the product_name or vice versa
    # e.g., stock "CARVALHO HANOVER" matches similarity table "CARVALHO HANOVER"
    candidates = conn.execute(
        "SELECT id, product_name FROM products WHERE brand = ? AND is_active = 1",
        (brand_db,),
    ).fetchall()

    for candidate in candidates:
        candidate_name = candidate["product_name"].upper()
        # Check if one name contains the other
        if candidate_name in short_name or short_name in candidate_name:
            return candidate["id"]

        # Check word overlap (at least 2 meaningful words match)
        short_words = set(short_name.split()) - {"DE", "DO", "DA", "E", "COM", "EM"}
        candidate_words = set(candidate_name.split()) - {"DE", "DO", "DA", "E", "COM", "EM"}
        common = short_words & candidate_words
        if len(common) >= 2:
            return candidate["id"]
        # Single word match if both names are single words
        if len(short_words) == 1 and len(candidate_words) == 1 and common:
            return candidate["id"]

    return None


def _update_product_details(conn, product_id: int, parsed: dict, erp_code: str, price: float | None):
    """Update an existing product with additional details from stock sheet."""
    updates = []
    params = []

    if parsed.get("thickness_mm"):
        updates.append("thickness_mm = ?")
        params.append(parsed["thickness_mm"])

    if parsed.get("finish"):
        updates.append("finish = ?")
        params.append(parsed["finish"])

    if erp_code:
        updates.append("product_code = ?")
        params.append(erp_code)

    if updates:
        params.append(product_id)
        conn.execute(
            f"UPDATE products SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params,
        )


def _upsert_stock(conn, product_id: int, quantity: float):
    """Insert or update stock entry for a product."""
    existing = conn.execute(
        "SELECT id FROM stock WHERE product_id = ?", (product_id,)
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE stock SET quantity_available = ?, last_updated = CURRENT_TIMESTAMP
               WHERE product_id = ?""",
            (quantity, product_id),
        )
    else:
        conn.execute(
            """INSERT INTO stock (product_id, quantity_available, quantity_reserved, last_updated)
               VALUES (?, ?, 0, CURRENT_TIMESTAMP)""",
            (product_id, quantity),
        )


def _create_stock_product(conn, parsed: dict, brand: str, erp_code: str, price: float | None) -> int | None:
    """Create a new product from stock data."""
    brand_upper = brand.upper()
    brand_map = {
        "PLACAS DO BRASIL": "PLACAS DO BRASIL",
        "PLACAS": "PLACAS DO BRASIL",
    }
    brand_db = brand_map.get(brand_upper, brand_upper)

    product_code = erp_code if erp_code else _generate_product_code(brand_db, parsed["short_name"])

    try:
        cursor = conn.execute(
            """INSERT INTO products
               (brand, product_name, product_code, thickness_mm, finish,
                category, is_active)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (
                brand_db,
                parsed["short_name"] or parsed["full_name"],
                product_code,
                parsed.get("thickness_mm"),
                parsed.get("finish"),
                _infer_category(parsed["short_name"] or parsed["full_name"]),
            ),
        )
        return cursor.lastrowid
    except Exception:
        return None


def _import_tape(conn, parsed: dict, brand: str, erp_code: str, stock_qty: float) -> int | None:
    """Import an edging tape product."""
    brand_upper = brand.upper()
    tape_name = parsed["short_name"] or parsed["full_name"]
    tape_code = erp_code if erp_code else _generate_product_code(brand_upper, tape_name)

    # Parse width from name (e.g., "22x0,45mm")
    width_match = re.search(r'(\d+)\s*x\s*\d', parsed["full_name"])
    width_mm = float(width_match.group(1)) if width_match else None

    # Parse thickness from name
    thickness_match = re.search(r'x\s*(\d+[.,]\d+)\s*mm', parsed["full_name"])
    tape_thickness = float(thickness_match.group(1).replace(",", ".")) if thickness_match else None

    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO edging_tapes
               (brand, tape_name, tape_code, width_mm, thickness_mm, color_family)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                brand_upper,
                tape_name,
                tape_code,
                width_mm,
                tape_thickness,
                _infer_category(tape_name),
            ),
        )
        return cursor.lastrowid if cursor.lastrowid else None
    except Exception:
        return None
