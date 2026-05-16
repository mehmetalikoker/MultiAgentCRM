# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock


# Modül yüklenirken Chroma/OpenAI çağrısını engelle
@pytest.fixture(autouse=True)
def mock_chroma_and_embeddings():
    mock_vs = MagicMock()
    mock_vs.similarity_search.return_value = [
        MagicMock(page_content="'Bedava' kelimesi kullanılamaz."),
        MagicMock(page_content="Faiz oranı yıllık maliyet oranıyla verilmelidir."),
    ]
    with patch("langchain_community.vectorstores.Chroma.from_texts", return_value=mock_vs), \
         patch("langchain_openai.OpenAIEmbeddings"):
        yield mock_vs


class TestComplianceChecker:
    def _make_llm_response(self, content: str) -> MagicMock:
        response = MagicMock()
        response.content = content
        return response

    def _run_checker(self, state: dict, llm_content: str):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = self._make_llm_response(llm_content)
        chain_mock = MagicMock()
        chain_mock.invoke.return_value = self._make_llm_response(llm_content)

        with patch("agents.llm_factory.get_llm", return_value=mock_llm), \
             patch("langchain_core.prompts.ChatPromptTemplate.from_template") as mock_tpl:
            mock_tpl.return_value.__or__ = lambda self, other: chain_mock
            from agents.campaigntextagent import compliance_checker
            return compliance_checker(state)

    def test_is_safe_true_when_response_contains_true(self):
        state = {
            "campaign_text": "Masrafsız kredi fırsatı, yıllık %14 faiz (YMO: %15.2).",
            "channel": "SMS",
            "selected_model": "gpt-4o",
        }
        llm_content = '{"is_safe": true, "report": "Uygun", "suggestions": []}'
        result = self._run_checker(state, llm_content)
        assert result["is_safe"] is True

    def test_is_safe_false_when_response_lacks_true(self):
        state = {
            "campaign_text": "Bedava kredi! Kesin onay garantili.",
            "channel": "Email",
            "selected_model": "gpt-4o",
        }
        llm_content = '{"is_safe": false, "report": "İhlal var.", "suggestions": ["Bedava yerine Masrafsız kullanın"]}'
        result = self._run_checker(state, llm_content)
        assert result["is_safe"] is False

    def test_compliance_report_stored_in_state(self):
        state = {
            "campaign_text": "Özel faiz oranı!",
            "channel": "Push Notification",
            "selected_model": "gpt-4o",
        }
        expected_report = '{"is_safe": true, "report": "Tamam.", "suggestions": []}'
        result = self._run_checker(state, expected_report)
        assert result["compliance_report"] == expected_report

    def test_default_model_used_when_not_specified(self):
        state = {
            "campaign_text": "Kredi kampanyası.",
            "channel": "SMS",
        }
        llm_content = '{"is_safe": true, "report": "OK", "suggestions": []}'
        with patch("agents.campaigntextagent.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            chain_mock = MagicMock()
            chain_mock.invoke.return_value = MagicMock(content=llm_content)
            mock_get_llm.return_value = mock_llm
            with patch("langchain_core.prompts.ChatPromptTemplate.from_template") as mock_tpl:
                mock_tpl.return_value.__or__ = lambda self, other: chain_mock
                from agents.campaigntextagent import compliance_checker
                compliance_checker(state)
            mock_get_llm.assert_called_once_with("gpt-4o")

    def test_channel_defaults_to_belirtilmedi_when_missing(self, mock_chroma_and_embeddings):
        state = {
            "campaign_text": "Kampanya metni.",
            "selected_model": "gpt-4o",
        }
        llm_content = '{"is_safe": true, "report": "Tamam", "suggestions": []}'
        captured_kwargs = {}

        mock_llm = MagicMock()
        chain_mock = MagicMock()
        chain_mock.invoke.side_effect = lambda kwargs: (
            captured_kwargs.update(kwargs) or MagicMock(content=llm_content)
        )

        with patch("agents.llm_factory.get_llm", return_value=mock_llm), \
             patch("langchain_core.prompts.ChatPromptTemplate.from_template") as mock_tpl:
            mock_tpl.return_value.__or__ = lambda self, other: chain_mock
            from agents.campaigntextagent import compliance_checker
            compliance_checker(state)

        assert captured_kwargs.get("channel") == "Belirtilmedi"


class TestRegulationsData:
    def test_regulations_list_is_not_empty(self):
        from agents.campaigntextagent import regulations_data
        assert len(regulations_data) > 0

    def test_bedava_rule_exists(self):
        from agents.campaigntextagent import regulations_data
        combined = " ".join(regulations_data)
        assert "Bedava" in combined

    def test_faiz_rule_exists(self):
        from agents.campaigntextagent import regulations_data
        combined = " ".join(regulations_data)
        assert "faiz" in combined.lower()

    def test_all_regulations_are_strings(self):
        from agents.campaigntextagent import regulations_data
        assert all(isinstance(r, str) for r in regulations_data)


class TestAgentStateSchema:
    def test_agent_state_has_required_keys(self):
        from agents.campaigntextagent import AgentState
        annotations = AgentState.__annotations__
        required_keys = {"campaign_text", "channel", "selected_model", "compliance_report", "is_safe", "suggestions"}
        assert required_keys.issubset(annotations.keys())
