"""Main chat interface component with image upload support."""

import base64
import streamlit as st
from src.services.substitution_orchestrator import SubstitutionOrchestrator
from config.settings import CLAUDE_API_KEY

# Tool name labels for user-friendly status messages
TOOL_LABELS = {
    "search_product": "Buscando produto...",
    "check_stock": "Verificando estoque...",
    "find_direct_equivalents": "Buscando equivalentes diretos...",
    "search_web_mdf": "Pesquisando na internet...",
    "find_compatible_edging_tape": "Buscando fita de borda...",
    "register_feedback": "Registrando feedback...",
    "generate_client_text": "Gerando texto para cliente...",
    "search_by_image": "Analisando imagem...",
}


def render_chat():
    """Render the main chat interface."""
    st.title("Agente MDF")
    st.caption("Copiloto inteligente para substituicao de MDF")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = _initialize_orchestrator()
    if "uploaded_image" not in st.session_state:
        st.session_state.uploaded_image = None

    # Check API key
    if not CLAUDE_API_KEY:
        st.warning(
            "Chave da API Anthropic nao configurada. "
            "Configure a variavel ANTHROPIC_API_KEY no arquivo .env ou nas Secrets do Streamlit."
        )
        return

    # Display message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("image_bytes"):
                st.image(msg["image_bytes"], width=300)
            st.markdown(msg["content"])

    # Image upload area (above chat input)
    uploaded_file = st.file_uploader(
        "Enviar foto de MDF (opcional)",
        type=["jpg", "jpeg", "png", "webp"],
        key="image_uploader",
        help="Tire uma foto ou envie imagem de catalogo para o sistema identificar o MDF",
    )

    # Store uploaded image in session state
    if uploaded_file is not None:
        st.session_state.uploaded_image = {
            "bytes": uploaded_file.getvalue(),
            "name": uploaded_file.name,
            "type": uploaded_file.type or "image/jpeg",
        }
        st.image(uploaded_file, caption="Imagem anexada", width=200)
    else:
        st.session_state.uploaded_image = None

    # Chat input
    if prompt := st.chat_input("Digite sua consulta sobre MDF..."):
        # Get image data if attached
        image_data = st.session_state.uploaded_image
        image_b64 = None
        image_media_type = None
        image_bytes_for_display = None

        if image_data:
            image_bytes_for_display = image_data["bytes"]
            image_b64 = base64.b64encode(image_data["bytes"]).decode("utf-8")
            image_media_type = image_data["type"]

        # Display user message
        display_msg = {
            "role": "user",
            "content": prompt,
        }
        if image_bytes_for_display:
            display_msg["image_bytes"] = image_bytes_for_display

        st.session_state.messages.append(display_msg)

        with st.chat_message("user"):
            if image_bytes_for_display:
                st.image(image_bytes_for_display, width=300)
            st.markdown(prompt)

        # Process through orchestrator with live status updates
        with st.chat_message("assistant"):
            status_container = st.empty()
            status_container.markdown("*Pensando...*")

            try:
                # Callback for tool progress updates
                def on_tool_call(tool_name: str):
                    label = TOOL_LABELS.get(tool_name, f"Executando {tool_name}...")
                    status_container.markdown(f"*{label}*")

                response_text, updated_history = (
                    st.session_state.orchestrator.process_message(
                        user_message=prompt,
                        conversation_history=st.session_state.conversation_history,
                        image_b64=image_b64,
                        image_media_type=image_media_type,
                        on_tool_call=on_tool_call,
                    )
                )
                st.session_state.conversation_history = updated_history

                # Replace status with final response
                status_container.empty()
                st.markdown(response_text)
            except Exception as e:
                response_text = f"Erro ao processar: {str(e)}"
                status_container.empty()
                st.error(response_text)

        st.session_state.messages.append(
            {"role": "assistant", "content": response_text}
        )

        # Clear the uploaded image after sending
        st.session_state.uploaded_image = None


def _initialize_orchestrator() -> SubstitutionOrchestrator:
    """Create the orchestrator instance."""
    return SubstitutionOrchestrator(api_key=CLAUDE_API_KEY)
