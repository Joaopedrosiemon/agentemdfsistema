import os
from pathlib import Path
from dotenv import load_dotenv

# Paths
PROJECT_ROOT = Path(__file__).parent.parent

# Load .env from project root
# Use stream for reliable unicode path support on Windows
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        load_dotenv(stream=_f, override=True)
else:
    load_dotenv()
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "db" / "mdf_agent.db"
RAW_DATA_DIR = DATA_DIR / "raw"
IMAGES_DIR = DATA_DIR / "images"
TEMPLATES_DIR = DATA_DIR / "templates"
BUNDLED_DIR = DATA_DIR / "bundled"

# Claude API
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))

# Web Search (Brave Search API)
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

# App
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

# Stock
DEFAULT_MIN_STOCK = 1.0
PRIMARY_LOCATION = os.getenv("PRIMARY_LOCATION", "principal")
CENTRAL_STOCK_FILE = Path(
    os.getenv("CENTRAL_STOCK_FILE", str(DATA_DIR / "raw" / "central_trocas.xlsx"))
)
CENTRAL_STOCK_REQUIRED = os.getenv("CENTRAL_STOCK_REQUIRED", "true").lower() in (
    "1",
    "true",
    "yes",
    "y",
)

# Search
FUZZY_MATCH_THRESHOLD = 0.6
MAX_SEARCH_RESULTS = 10

# Similarity (Claude Vision)
MAX_VISUAL_CANDIDATES_PER_BATCH = 5
SIMILARITY_CACHE_DAYS = 30

# Edging tape stock
TAPE_METERS_PER_ROLL = float(os.getenv("TAPE_METERS_PER_ROLL", "20"))

# Import - column name mappings (Portuguese -> English)
PRODUCT_COLUMN_MAP = {
    "marca": "brand",
    "brand": "brand",
    "nome": "product_name",
    "padrao": "product_name",
    "padrão": "product_name",
    "pattern": "product_name",
    "product_name": "product_name",
    "codigo": "product_code",
    "código": "product_code",
    "code": "product_code",
    "product_code": "product_code",
    "espessura": "thickness_mm",
    "thickness": "thickness_mm",
    "thickness_mm": "thickness_mm",
    "acabamento": "finish",
    "finish": "finish",
    "largura": "width_mm",
    "width": "width_mm",
    "width_mm": "width_mm",
    "altura": "height_mm",
    "height": "height_mm",
    "height_mm": "height_mm",
    "familia_cor": "color_family",
    "cor": "color_family",
    "color_family": "color_family",
    "categoria": "category",
    "category": "category",
    "imagem": "image_path",
    "image": "image_path",
    "image_path": "image_path",
}

STOCK_COLUMN_MAP = {
    "codigo": "product_code",
    "código": "product_code",
    "code": "product_code",
    "product_code": "product_code",
    "quantidade": "quantity_available",
    "qtd": "quantity_available",
    "quantity": "quantity_available",
    "quantity_available": "quantity_available",
    "reservado": "quantity_reserved",
    "reserved": "quantity_reserved",
    "quantity_reserved": "quantity_reserved",
    "minimo": "minimum_stock",
    "mínimo": "minimum_stock",
    "minimum": "minimum_stock",
    "minimum_stock": "minimum_stock",
    "localizacao": "location",
    "localização": "location",
    "location": "location",
    "loja": "location",
    "filial": "location",
    "store": "location",
    "branch": "location",
    "unidade": "unit",
    "unit": "unit",
    "saldo": "quantity_available",
    "cod_produto": "product_code",
    "codigo_produto": "product_code",
    "empresa": "location",
    "secao": "section",
    "section": "section",
    "produto": "product_name",
    "marca": "brand",

}

EQUIVALENCE_COLUMN_MAP = {
    "codigo_a": "code_a",
    "código_a": "code_a",
    "code_a": "code_a",
    "produto_a": "product_name_a",
    "product_a": "product_name_a",
    "product_name_a": "product_name_a",
    "marca_a": "brand_a",
    "brand_a": "brand_a",
    "codigo_b": "code_b",
    "código_b": "code_b",
    "code_b": "code_b",
    "produto_b": "product_name_b",
    "product_b": "product_name_b",
    "product_name_b": "product_name_b",
    "marca_b": "brand_b",
    "brand_b": "brand_b",
    "fonte": "equivalence_source",
    "source": "equivalence_source",
    "equivalence_source": "equivalence_source",
    "confianca": "confidence",
    "confiança": "confidence",
    "confidence": "confidence",
}

TAPE_COLUMN_MAP = {
    "marca": "brand",
    "brand": "brand",
    "nome": "tape_name",
    "tape_name": "tape_name",
    "codigo": "tape_code",
    "código": "tape_code",
    "code": "tape_code",
    "tape_code": "tape_code",
    "largura": "width_mm",
    "width": "width_mm",
    "width_mm": "width_mm",
    "espessura": "thickness_mm",
    "thickness": "thickness_mm",
    "thickness_mm": "thickness_mm",
    "acabamento": "finish",
    "finish": "finish",
    "familia_cor": "color_family",
    "cor": "color_family",
    "color_family": "color_family",
    "quantidade": "quantity_available",
    "qtd": "quantity_available",
    "estoque": "quantity_available",
    "quantity": "quantity_available",
    "quantity_available": "quantity_available",
    "stock": "quantity_available",
}

# Supported file types for import
SUPPORTED_FILE_TYPES = [".csv", ".xlsx", ".xls"]
