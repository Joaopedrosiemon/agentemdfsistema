"""Copy-to-clipboard functionality."""

import streamlit as st


def render_copyable_text(text: str, key: str = "copy"):
    """Render text with a copy button."""
    st.code(text, language=None)
    st.caption("Use o botao de copiar no canto superior direito do bloco acima.")
