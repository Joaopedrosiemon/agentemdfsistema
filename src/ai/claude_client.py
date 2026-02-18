"""Anthropic Claude API wrapper."""

import anthropic
from config.settings import CLAUDE_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS


class ClaudeClient:
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key or CLAUDE_API_KEY)
        self.model = CLAUDE_MODEL

    def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = None,
    ) -> anthropic.types.Message:
        """Send a chat request to Claude with optional tools."""
        params = {
            "model": self.model,
            "max_tokens": max_tokens or CLAUDE_MAX_TOKENS,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            params["tools"] = tools
        return self.client.messages.create(**params)
