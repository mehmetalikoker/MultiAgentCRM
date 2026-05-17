# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock


class TestGetLlm:
    def test_gpt_model_returns_chatopenai(self):
        mock_instance = MagicMock()
        with patch("langchain_openai.ChatOpenAI", return_value=mock_instance) as mock_cls:
            from agents.llm_factory import get_llm
            result = get_llm("gpt-4o")
            mock_cls.assert_called_once_with(model="gpt-4o", temperature=0)
            assert result is mock_instance

    def test_claude_model_returns_chatanthropic(self):
        mock_instance = MagicMock()
        mock_module = MagicMock()
        mock_module.ChatAnthropic.return_value = mock_instance
        with patch.dict("sys.modules", {"langchain_anthropic": mock_module}):
            import importlib, agents.llm_factory as llm_mod
            importlib.reload(llm_mod)
            result = llm_mod.get_llm("claude-opus-4-7")
            mock_module.ChatAnthropic.assert_called_once_with(model="claude-opus-4-7")
            assert result is mock_instance

    def test_gemini_model_returns_chatgoogle(self):
        mock_instance = MagicMock()
        mock_module = MagicMock()
        mock_module.ChatGoogleGenerativeAI.return_value = mock_instance
        with patch.dict("sys.modules", {"langchain_google_genai": mock_module}):
            with patch.dict("os.environ", {"GEMINI_API_KEY": "test-gemini-key"}):
                import importlib, agents.llm_factory as llm_mod
                importlib.reload(llm_mod)
                result = llm_mod.get_llm("gemini-1.5-pro")
                call_kwargs = mock_module.ChatGoogleGenerativeAI.call_args.kwargs
                assert call_kwargs["model"] == "gemini-1.5-pro"
                assert call_kwargs["temperature"] == 0
                assert call_kwargs["google_api_key"] == "test-gemini-key"
                assert result is mock_instance

    def test_deepseek_model_uses_openai_with_custom_base_url(self):
        mock_instance = MagicMock()
        with patch("langchain_openai.ChatOpenAI", return_value=mock_instance) as mock_cls:
            with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}):
                from agents.llm_factory import get_llm
                result = get_llm("deepseek-chat")
                call_kwargs = mock_cls.call_args.kwargs
                assert call_kwargs["base_url"] == "https://api.deepseek.com"
                assert result is mock_instance

    def test_unknown_model_falls_back_to_chatopenai(self):
        mock_instance = MagicMock()
        with patch("langchain_openai.ChatOpenAI", return_value=mock_instance) as mock_cls:
            from agents.llm_factory import get_llm
            result = get_llm("some-unknown-model")
            mock_cls.assert_called_once_with(model="some-unknown-model", temperature=0)
            assert result is mock_instance

    def test_custom_temperature_is_passed(self):
        mock_instance = MagicMock()
        with patch("langchain_openai.ChatOpenAI", return_value=mock_instance) as mock_cls:
            from agents.llm_factory import get_llm
            get_llm("gpt-4o", temperature=0.7)
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs["temperature"] == 0.7

    @pytest.mark.parametrize("model_name,expected_class_attr", [
        ("gpt-3.5-turbo", "ChatOpenAI"),
        ("gpt-4-turbo", "ChatOpenAI"),
        ("deepseek-coder", "ChatOpenAI"),
    ])
    def test_openai_based_model_routing(self, model_name, expected_class_attr):
        mock_instance = MagicMock()
        with patch("langchain_openai.ChatOpenAI", return_value=mock_instance):
            from agents.llm_factory import get_llm
            result = get_llm(model_name)
            assert result is mock_instance

    def test_claude_routing(self):
        mock_instance = MagicMock()
        mock_module = MagicMock()
        mock_module.ChatAnthropic.return_value = mock_instance
        with patch.dict("sys.modules", {"langchain_anthropic": mock_module}):
            import importlib, agents.llm_factory as llm_mod
            importlib.reload(llm_mod)
            result = llm_mod.get_llm("claude-sonnet-4-6")
            assert result is mock_instance

    def test_gemini_routing(self):
        mock_instance = MagicMock()
        mock_module = MagicMock()
        mock_module.ChatGoogleGenerativeAI.return_value = mock_instance
        with patch.dict("sys.modules", {"langchain_google_genai": mock_module}):
            import importlib, agents.llm_factory as llm_mod
            importlib.reload(llm_mod)
            result = llm_mod.get_llm("gemini-pro")
            assert result is mock_instance
