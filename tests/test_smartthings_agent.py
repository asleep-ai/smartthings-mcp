"""Unit tests for SmartThings Agent handler."""

import os
from unittest.mock import patch

import pytest

from smartthings_agent.handler import (
    MODEL_ID,
    RESPONSE_ID_PREFIX,
    SmartThingsAgentError,
    SmartThingsLLM,
    _DEFAULT_CWD,
)


class TestConstants:
    """Test module constants."""

    def test_model_id(self):
        assert MODEL_ID == "smartthings/agent"

    def test_response_id_prefix(self):
        assert RESPONSE_ID_PREFIX == "chatcmpl-smartthings"

    def test_default_cwd_is_project_root(self):
        # _DEFAULT_CWD should point to project root (3 levels up from handler.py)
        assert _DEFAULT_CWD.exists()
        assert (_DEFAULT_CWD / "pyproject.toml").exists()


class TestMessagesToPrompt:
    """Test _messages_to_prompt method."""

    def setup_method(self):
        self.handler = SmartThingsLLM()

    def test_extracts_last_user_message(self):
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Second message"},
        ]
        result = self.handler._messages_to_prompt(messages)
        assert result == "Second message"

    def test_handles_single_user_message(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = self.handler._messages_to_prompt(messages)
        assert result == "Hello"

    def test_handles_content_blocks_format(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "text", "text": "World"},
                ],
            }
        ]
        result = self.handler._messages_to_prompt(messages)
        assert result == "Hello World"

    def test_ignores_non_text_blocks(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": "http://example.com/img.png"},
                    {"type": "text", "text": "Describe this"},
                ],
            }
        ]
        result = self.handler._messages_to_prompt(messages)
        assert result == "Describe this"

    def test_raises_on_no_user_message(self):
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "Hello!"},
        ]
        with pytest.raises(ValueError, match="No user message found"):
            self.handler._messages_to_prompt(messages)

    def test_raises_on_empty_messages(self):
        with pytest.raises(ValueError, match="No user message found"):
            self.handler._messages_to_prompt([])


class TestMakeResponse:
    """Test _make_response method."""

    def setup_method(self):
        self.handler = SmartThingsLLM()

    def test_creates_model_response(self):
        response = self.handler._make_response("Hello, world!")

        assert response.id == RESPONSE_ID_PREFIX
        assert response.model == MODEL_ID
        assert len(response.choices) == 1
        assert response.choices[0].message.content == "Hello, world!"
        assert response.choices[0].message.role == "assistant"
        assert response.choices[0].finish_reason == "stop"

    def test_usage_is_zero(self):
        response = self.handler._make_response("Test")

        assert response.usage.prompt_tokens == 0
        assert response.usage.completion_tokens == 0
        assert response.usage.total_tokens == 0

    def test_handles_empty_string(self):
        response = self.handler._make_response("")
        assert response.choices[0].message.content == ""


class TestGetAgentOptions:
    """Test _get_agent_options method."""

    def setup_method(self):
        self.handler = SmartThingsLLM()

    def test_uses_default_cwd(self):
        options = self.handler._get_agent_options()
        assert options.cwd == str(_DEFAULT_CWD)

    def test_respects_env_var(self):
        custom_path = "/custom/path"
        with patch.dict(os.environ, {"SMARTTHINGS_MCP_PATH": custom_path}):
            options = self.handler._get_agent_options()
            assert options.cwd == custom_path

    def test_uses_haiku_model(self):
        options = self.handler._get_agent_options()
        assert options.model == "haiku"

    def test_has_required_tools(self):
        options = self.handler._get_agent_options()
        assert "Skill" in options.allowed_tools
        assert "Bash" in options.allowed_tools
        assert "Grep" in options.allowed_tools


class TestSmartThingsAgentError:
    """Test SmartThingsAgentError exception."""

    def test_inherits_from_exception(self):
        assert issubclass(SmartThingsAgentError, Exception)

    def test_can_be_raised_with_message(self):
        with pytest.raises(SmartThingsAgentError, match="Test error"):
            raise SmartThingsAgentError("Test error")

    def test_can_chain_exceptions(self):
        original = ValueError("Original error")
        try:
            raise SmartThingsAgentError("Wrapped") from original
        except SmartThingsAgentError as e:
            assert e.__cause__ is original
