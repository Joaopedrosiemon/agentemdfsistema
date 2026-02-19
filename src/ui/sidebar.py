"""Sidebar component — data import, stats, settings."""

import streamlit as st

from src.database.schema import initialize_database
from src.database.import_data import (
    import_products,
    import_stock,
    import_equivalences,
    import_edging_tapes,
)
from src.database.preload_data import (
    is_data_preloaded,
    preload_similarity_table,
    is_stock_preloaded,
    preload_stock,
)
from src.database import queries
from src.ui.components import render_import_result
from config.constants import IMPORT_TYPES


def render_sidebar():
    """Render the sidebar with import and stats sections."""
    with st.sidebar:
        st.header("Agente MDF")
        st.caption("Copiloto de Substituicao v1.3.1")

        st.divider()

        # ── Database Stats ─────────────────────────
        st.subheader("Status da Base")
        _show_database_stats()

        st.divider()

        # ── Data Import ────────────────────────────
        with st.expander("Importar Dados Adicionais", expanded=False):
            uploaded_file = st.file_uploader(
                "Carregar planilha",
                type=["csv", "xlsx", "xls"],
                help="Importe dados de produtos, estoque, equivalencias ou fitas de borda",
            )

            import_type = st.selectbox(
                "Tipo de dado",
                list(IMPORT_TYPES.keys()),
            )

            if st.button("Importar", use_container_width=True, disabled=uploaded_file is None):
                if uploaded_file:
                    _handle_import(uploaded_file, import_type)

        st.divider()

        # ── Actions ────────────────────────────────
        with st.expander("Acoes Avancadas", expanded=False):
            if st.button("Recarregar Base de Similaridade", use_container_width=True):
                from src.database.connection import get_connection
                conn = get_connection()
                conn.execute(
                    "DELETE FROM import_log WHERE file_name = 'PRELOAD_SIMILARITY_TABLE'"
                )
                conn.execute(
                    "DELETE FROM direct_equivalences WHERE equivalence_source = 'Tabela Similaridade Grupo Locatelli'"
                )
                conn.commit()

                result = preload_similarity_table()
                if result.get("success"):
                    st.success(
                        f"Similaridade recarregada: {result.get('products_created', 0)} produtos, "
                        f"{result.get('equivalences_created', 0)} equivalencias"
                    )
                else:
                    st.error(f"Erro: {result.get('error', 'Desconhecido')}")
                st.rerun()

            if st.button("Recarregar Estoque", use_container_width=True):
                from src.database.connection import get_connection
                conn = get_connection()
                conn.execute("DELETE FROM import_log WHERE file_name = 'PRELOAD_STOCK'")
                conn.execute("DELETE FROM stock")
                conn.commit()

                result = preload_stock()
                if result.get("success"):
                    st.success(
                        f"Estoque recarregado: {result.get('stock_entries', 0)} itens, "
                        f"{result.get('products_updated', 0)} vinculados"
                    )
                else:
                    st.error(f"Erro: {result.get('error', 'Desconhecido')}")
                st.rerun()

            if st.button("Inicializar Banco de Dados", use_container_width=True):
                initialize_database()
                st.success("Banco de dados inicializado!")
                st.rerun()


def _handle_import(uploaded_file, import_type: str):
    """Process file import based on type."""
    file_name = uploaded_file.name
    data_type = IMPORT_TYPES[import_type]

    with st.spinner(f"Importando {import_type}..."):
        if data_type == "products":
            result = import_products(uploaded_file, file_name)
        elif data_type == "stock":
            result = import_stock(uploaded_file, file_name)
        elif data_type == "equivalences":
            result = import_equivalences(uploaded_file, file_name)
        elif data_type == "tapes":
            result = import_edging_tapes(uploaded_file, file_name)
        else:
            st.error(f"Tipo desconhecido: {data_type}")
            return

    render_import_result(result)


def _show_database_stats():
    """Display database statistics."""
    try:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Produtos", queries.count_products())
            st.metric("Equivalencias", queries.count_equivalences())
        with col2:
            st.metric("Estoque", queries.count_stock_entries())
            st.metric("Fitas", queries.count_tapes())

        if is_data_preloaded():
            st.caption("✅ Tabela Similaridade carregada")
        else:
            st.caption("⚠️ Tabela Similaridade nao carregada")

        if is_stock_preloaded():
            st.caption("✅ Estoque carregado")
        else:
            st.caption("⚠️ Estoque nao carregado")

        from config.settings import BRAVE_API_KEY
        if BRAVE_API_KEY:
            st.caption("✅ Pesquisa web ativa")
        else:
            st.caption("ℹ️ Pesquisa web nao configurada")
    except Exception:
        st.caption("Banco de dados nao inicializado. Clique em 'Inicializar Banco de Dados'.")
