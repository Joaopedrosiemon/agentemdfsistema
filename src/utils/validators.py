"""Data validation for imports."""

import pandas as pd


class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)


def validate_product_dataframe(df: pd.DataFrame) -> ValidationResult:
    result = ValidationResult()
    required = ["brand", "product_name", "product_code"]
    for col in required:
        if col not in df.columns:
            result.add_error(f"Coluna obrigatoria ausente: '{col}'")
    if not result.is_valid:
        return result

    nulls = df[required].isnull().sum()
    for col in required:
        if nulls[col] > 0:
            result.add_error(f"Coluna '{col}' tem {nulls[col]} valores nulos")

    dupes = df["product_code"].duplicated().sum()
    if dupes > 0:
        result.add_warning(f"{dupes} codigos duplicados encontrados (serão ignorados)")

    if "thickness_mm" in df.columns:
        non_numeric = pd.to_numeric(df["thickness_mm"], errors="coerce").isna() & df["thickness_mm"].notna()
        if non_numeric.sum() > 0:
            result.add_warning(f"{non_numeric.sum()} valores de espessura nao numericos")

    return result


def validate_stock_dataframe(df: pd.DataFrame) -> ValidationResult:
    result = ValidationResult()
    if "product_code" not in df.columns:
        result.add_error("Coluna obrigatoria ausente: 'product_code'")
    if "quantity_available" not in df.columns:
        result.add_error("Coluna obrigatoria ausente: 'quantity_available'")
    if not result.is_valid:
        return result

    nulls = df["product_code"].isnull().sum()
    if nulls > 0:
        result.add_error(f"Coluna 'product_code' tem {nulls} valores nulos")

    return result


def validate_equivalence_dataframe(df: pd.DataFrame) -> ValidationResult:
    result = ValidationResult()
    # Must have either codes or names+brands for both sides
    has_codes = "code_a" in df.columns and "code_b" in df.columns
    has_names = all(c in df.columns for c in ["product_name_a", "brand_a", "product_name_b", "brand_b"])

    if not has_codes and not has_names:
        result.add_error(
            "Tabela de equivalencia precisa ter 'code_a' e 'code_b', "
            "ou 'product_name_a', 'brand_a', 'product_name_b', 'brand_b'"
        )
    return result


def validate_tape_dataframe(df: pd.DataFrame) -> ValidationResult:
    result = ValidationResult()
    required = ["brand", "tape_name", "tape_code"]
    for col in required:
        if col not in df.columns:
            result.add_error(f"Coluna obrigatoria ausente: '{col}'")
    return result
