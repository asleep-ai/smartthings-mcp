"""CustomLLM handler for litellm that uses Claude Agent SDK with SmartThings skills."""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    query,
)
from litellm import CustomLLM
from litellm.types.utils import Choices, Message, ModelResponse, Usage

logger = logging.getLogger(__name__)

# Constants
MODEL_ID = "smartthings/agent"
RESPONSE_ID_PREFIX = "chatcmpl-smartthings"

# Default working directory (can be overridden via SMARTTHINGS_MCP_PATH env var)
_DEFAULT_CWD = Path(__file__).parent.parent.parent


class SmartThingsAgentError(Exception):
    """Error from SmartThings agent communication."""

    pass


class SmartThingsLLM(CustomLLM):
    """LiteLLM custom handler that routes to Claude Agent SDK with SmartThings skills."""

    def _get_agent_options(self) -> ClaudeAgentOptions:
        """Get shared agent options."""
        cwd = os.environ.get("SMARTTHINGS_MCP_PATH", str(_DEFAULT_CWD))
        return ClaudeAgentOptions(
            cwd=cwd,
            setting_sources=["project"],
            model="haiku",
            allowed_tools=["Skill", "Bash", "Grep"],
            system_prompt=(
                "You are a smart home assistant. Use the SmartThings skill "
                "iteratively to control devices. Read SKILL.md for usage "
                "instructions. Be concise in responses."
            ),
        )

    def completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ModelResponse:
        """Handle completion request by routing to Agent SDK.

        Args:
            model: Model name (ignored, uses Agent SDK's model)
            messages: OpenAI-format messages
            **kwargs: Additional arguments (ignored)

        Returns:
            ModelResponse with agent's response
        """
        prompt = self._messages_to_prompt(messages)

        # Check if we're already in an async context
        try:
            asyncio.get_running_loop()
            # In async context - run in thread pool
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                response_text = pool.submit(
                    asyncio.run, self._run_agent(prompt)
                ).result()
        except RuntimeError:
            # No event loop - safe to use asyncio.run
            response_text = asyncio.run(self._run_agent(prompt))

        return self._make_response(response_text)

    async def acompletion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ModelResponse:
        """Handle async completion request."""
        prompt = self._messages_to_prompt(messages)
        response_text = await self._run_agent(prompt)
        return self._make_response(response_text)

    def _make_response(self, response_text: str) -> ModelResponse:
        """Create ModelResponse from text.

        Note: Token usage is not tracked by Claude Agent SDK, so usage is reported as 0.
        """
        return ModelResponse(
            id=RESPONSE_ID_PREFIX,
            choices=[
                Choices(
                    index=0,
                    message=Message(role="assistant", content=response_text),
                    finish_reason="stop",
                )
            ],
            model=MODEL_ID,
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

    async def astreaming(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Handle async streaming completion request."""
        prompt = self._messages_to_prompt(messages)

        async for text in self._query_agent(prompt):
            yield {
                "text": text,
                "is_finished": False,
                "finish_reason": None,
                "usage": None,
                "index": 0,
            }

        yield {
            "text": "",
            "is_finished": True,
            "finish_reason": "stop",
            "usage": None,
            "index": 0,
        }

    async def _query_agent(self, prompt: str) -> AsyncIterator[str]:
        """Query agent and yield text chunks.

        Raises:
            SmartThingsAgentError: If agent communication fails.
        """
        try:
            async for message in query(prompt=prompt, options=self._get_agent_options()):
                logger.debug(f"[agent] message: {message}")
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield block.text
        except Exception as e:
            logger.error(f"[agent] error: {e}")
            raise SmartThingsAgentError(f"Agent communication failed: {e}") from e

    async def _run_agent(self, prompt: str) -> str:
        """Run agent and return full response text.

        Raises:
            SmartThingsAgentError: If agent communication fails or returns empty.
        """
        result = ""
        async for text in self._query_agent(prompt):
            result += text

        if not result.strip():
            logger.warning("[agent] empty response received")

        return result

    def _messages_to_prompt(self, messages: list[dict[str, Any]]) -> str:
        """Extract the last user message as prompt.

        Args:
            messages: OpenAI-format messages list

        Returns:
            Last user message content

        Raises:
            ValueError: If no user message is found in the messages.
        """
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                # Handle content blocks format
                if isinstance(content, list):
                    return " ".join(
                        block.get("text", "")
                        for block in content
                        if block.get("type") == "text"
                    )
        raise ValueError("No user message found in messages")


# Instance for litellm proxy config
smartthings_llm = SmartThingsLLM()
