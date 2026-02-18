"""Reusable UI components for the MDF Agent."""

import streamlit as st


def render_product_card(product: dict):
    """Render a product info card."""
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{product.get('brand', '')} {product.get('product_name', '')}**")
            st.caption(f"Codigo: {product.get('product_code', '')}")
            details = []
            if product.get("thickness_mm"):
                details.append(f"Espessura: {product['thickness_mm']}mm")
            if product.get("finish"):
                details.append(f"Acabamento: {product['finish']}")
            if product.get("category"):
                details.append(f"Categoria: {product['category']}")
            if details:
                st.caption(" | ".join(details))
        with col2:
            render_stock_badge(product.get("quantity_available", 0), product.get("quantity_reserved", 0))


def render_stock_badge(qty_available: float, qty_reserved: float = 0):
    """Render a colored stock badge."""
    net = qty_available - qty_reserved
    if net > 10:
        st.success(f"Em estoque: {int(net)}")
    elif net > 0:
        st.warning(f"Estoque baixo: {int(net)}")
    else:
        st.error("Sem estoque")


def render_import_result(result):
    """Render import result feedback."""
    if result.success:
        st.success(f"Importados: {result.rows_imported} registros")
        if result.rows_failed > 0:
            st.warning(f"Falhas: {result.rows_failed} registros")
    else:
        st.error("Falha na importacao")

    for error in result.errors:
        st.error(error)
    for warning in result.warnings:
        st.warning(warning)
