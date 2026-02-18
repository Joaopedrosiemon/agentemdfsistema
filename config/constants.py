"""Constants and enums for the MDF Agent system."""

# Product categories
CATEGORIES = ["Madeirado", "Unicolor", "Fantasia", "Conceito"]

# Tape compatibility types
TAPE_COMPATIBILITY_TYPES = ["official", "recommended", "alternative"]

# Feedback suggestion types
SUGGESTION_TYPES = ["direct_equivalence", "visual_similarity"]

# Import data types
IMPORT_TYPES = {
    "Produtos MDF": "products",
    "Estoque": "stock",
    "Equivalências": "equivalences",
    "Fitas de Borda": "tapes",
}

# Import statuses
IMPORT_STATUSES = ["pending", "success", "partial", "failed"]
