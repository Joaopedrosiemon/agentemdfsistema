"""MDF Agent — Intelligent Substitution Copilot."""

import streamlit as st
from config.settings import APP_PASSWORD
from src.database.schema import initialize_database
from src.database.preload_data import (
    preload_similarity_table,
    is_data_preloaded,
    preload_stock,
    is_stock_preloaded,
)

st.set_page_config(
    page_title="Agente MDF - Copiloto de Substituicao",
    page_icon="🪵",
    layout="wide",
)

# Initialize database on first run
initialize_database()

# Auto-load bundled data (Grupo Locatelli similarity table + stock)
if not is_data_preloaded():
    with st.spinner("Carregando base de dados de similaridade..."):
        result = preload_similarity_table()
        if result.get("success") and result.get("products_created", 0) > 0:
            st.toast(
                f"Similaridade: {result.get('products_created', 0)} produtos, "
                f"{result.get('equivalences_created', 0)} equivalencias",
                icon="✅",
            )
        elif result.get("error"):
            st.toast(f"Aviso: {result['error']}", icon="⚠️")

if not is_stock_preloaded():
    with st.spinner("Carregando estoque..."):
        result = preload_stock()
        if result.get("success") and result.get("stock_entries", 0) > 0:
            st.toast(
                f"Estoque: {result.get('stock_entries', 0)} itens, "
                f"{result.get('products_updated', 0)} vinculados, "
                f"{result.get('tapes_created', 0)} fitas",
                icon="✅",
            )
        elif result.get("error"):
            st.toast(f"Aviso estoque: {result['error']}", icon="⚠️")


def check_password() -> bool:
    """Simple password authentication."""
    if not APP_PASSWORD:
        return True  # No password configured, allow access

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("Agente MDF")
    st.caption("Copiloto inteligente para substituicao de MDF")

    password = st.text_input("Senha de acesso", type="password")
    if st.button("Entrar", use_container_width=True):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Senha incorreta")

    return False


if check_password():
    from src.ui.sidebar import render_sidebar
    from src.ui.chat_interface import render_chat

    render_sidebar()
    render_chat()
