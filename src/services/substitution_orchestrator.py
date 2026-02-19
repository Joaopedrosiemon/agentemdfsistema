"""Central orchestrator for the Claude tool_use conversation loop."""

import json
import uuid

from src.ai.claude_client import ClaudeClient
from src.ai.prompts import SYSTEM_PROMPT
from src.ai.tools import TOOLS
from src.ai.response_formatter import generate_client_text
from src.services import (
    product_service,
    stock_service,
    equivalence_service,
    similarity_service,
    web_search_service,
    edging_tape_service,
    feedback_service,
)


class SubstitutionOrchestrator:
    def __init__(self, api_key: str = None):
        self.client = ClaudeClient(api_key=api_key)
        self.session_id = str(uuid.uuid4())
        self._pending_image_b64 = None
        self._pending_image_media_type = None
        self.tool_handlers = {
            "search_product": self._handle_search_product,
            "check_stock": self._handle_check_stock,
            "find_direct_equivalents": self._handle_find_equivalents,
            "search_web_mdf": self._handle_web_search,
            "find_compatible_edging_tape": self._handle_find_tape,
            "register_feedback": self._handle_register_feedback,
            "generate_client_text": self._handle_generate_text,
            "search_by_image": self._handle_search_by_image,
        }

    def process_message(
        self,
        user_message: str,
        conversation_history: list[dict],
        image_b64: str | None = None,
        image_media_type: str | None = None,
        on_tool_call: callable = None,
    ) -> tuple[str, list[dict]]:
        """
        Process a user message through the full tool-use loop.
        Supports optional image attachment.
        on_tool_call: optional callback(tool_name) for UI progress updates.
        Returns: (assistant_response_text, updated_conversation_history)
        """
        # Store image for tool handlers to access
        self._pending_image_b64 = image_b64
        self._pending_image_media_type = image_media_type

        # Build message content (text-only or text+image)
        if image_b64:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type or "image/jpeg",
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": user_message,
                },
            ]
        else:
            content = user_message

        conversation_history.append({"role": "user", "content": content})

        max_iterations = 8  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = self.client.chat(
                messages=conversation_history,
                system_prompt=SYSTEM_PROMPT,
                tools=TOOLS,
            )

            # Check for tool_use blocks
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # Pure text response — conversation turn is done
                text_parts = [b.text for b in response.content if b.type == "text"]
                text = "".join(text_parts)
                conversation_history.append(
                    {"role": "assistant", "content": response.content}
                )
                # Clear pending image after processing
                self._pending_image_b64 = None
                self._pending_image_media_type = None
                return text, conversation_history

            # Process tool calls
            conversation_history.append(
                {"role": "assistant", "content": response.content}
            )

            tool_results = []
            for tool_block in tool_use_blocks:
                # Notify UI about which tool is being called
                if on_tool_call:
                    try:
                        on_tool_call(tool_block.name)
                    except Exception:
                        pass

                handler = self.tool_handlers.get(tool_block.name)
                if handler:
                    try:
                        result = handler(**tool_block.input)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Ferramenta desconhecida: {tool_block.name}"}

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(
                            result, ensure_ascii=False, default=str
                        ),
                    }
                )

            conversation_history.append({"role": "user", "content": tool_results})

        # If we hit max iterations, return what we have
        self._pending_image_b64 = None
        self._pending_image_media_type = None
        return (
            "Desculpe, nao consegui completar a analise. Pode reformular sua pergunta?",
            conversation_history,
        )

    # ── Tool Handlers ────────────────────────────────────

    def _handle_search_product(self, query: str) -> list[dict]:
        results = product_service.search(query)
        return [
            {
                "id": r["id"],
                "brand": r["brand"],
                "product_name": r["product_name"],
                "product_code": r["product_code"],
                "thickness_mm": r.get("thickness_mm"),
                "finish": r.get("finish"),
                "category": r.get("category"),
                "in_stock": r.get("in_stock", False),
                "quantity_available": r.get("quantity_available", 0),
                "match_score": r.get("match_score", 0),
                "match_type": r.get("match_type", ""),
            }
            for r in results
        ]

    def _handle_check_stock(
        self,
        product_id: int,
        include_other_locations: bool = False,
    ) -> dict:
        return stock_service.check_availability(
            product_id, include_other_locations=include_other_locations
        )

    def _handle_find_equivalents(
        self, product_id: int, require_same_thickness: bool = True
    ) -> list[dict]:
        results = equivalence_service.find_direct_equivalents(
            product_id, require_same_thickness=require_same_thickness
        )
        return [
            {
                "id": r["id"],
                "brand": r["brand"],
                "product_name": r["product_name"],
                "product_code": r["product_code"],
                "thickness_mm": r.get("thickness_mm"),
                "finish": r.get("finish"),
                "net_available": r.get("net_available", 0),
                "equivalence_source": r.get("equivalence_source"),
                "confidence": r.get("confidence", 1.0),
            }
            for r in results
        ]

    def _handle_web_search(
        self, product_name: str, brand: str = ""
    ) -> dict:
        return web_search_service.search_web_and_cross_reference(product_name, brand)

    def _handle_find_tape(self, product_id: int) -> list[dict]:
        results = edging_tape_service.find_compatible(product_id)
        return [
            {
                "id": r["id"],
                "brand": r["brand"],
                "tape_name": r["tape_name"],
                "tape_code": r["tape_code"],
                "width_mm": r.get("width_mm"),
                "thickness_mm": r.get("thickness_mm"),
                "compatibility_type": r.get("compatibility_type", "alternative"),
                "quantity_available": r.get("quantity_available", 0),
                "quantity_available_meters": r.get("quantity_available_meters", 0),
                "unit": r.get("unit", "rolos"),
                "in_stock": r.get("in_stock", False),
                "match_score": r.get("match_score", 0),
            }
            for r in results
        ]

    def _handle_register_feedback(
        self,
        original_product_id: int,
        suggested_product_id: int,
        accepted: bool,
        rating: int | None = None,
        comment: str | None = None,
    ) -> dict:
        return feedback_service.save(
            session_id=self.session_id,
            original_product_id=original_product_id,
            suggested_product_id=suggested_product_id,
            suggestion_type="direct_equivalence",
            accepted=accepted,
            rating=rating,
            comment=comment,
        )

    def _handle_generate_text(
        self,
        original_product_id: int,
        suggested_product_id: int,
        suggestion_type: str,
    ) -> dict:
        return generate_client_text(
            original_product_id, suggested_product_id, suggestion_type
        )

    def _handle_search_by_image(self, max_results: int = 5) -> list[dict]:
        """Handle image-based search using the pending uploaded image."""
        if not self._pending_image_b64:
            return [{"error": "Nenhuma imagem foi enviada pelo vendedor nesta mensagem."}]

        results = similarity_service.search_by_uploaded_image(
            image_b64=self._pending_image_b64,
            image_media_type=self._pending_image_media_type or "image/jpeg",
            max_results=max_results,
        )
        return results
