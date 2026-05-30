# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def mock_chroma_and_embeddings():
    mock_vs = MagicMock()
    mock_vs.similarity_search.return_value = [
        MagicMock(page_content="BDDK faiz oranı gösterimi zorunludur."),
        MagicMock(page_content="Kampanya bitiş tarihi belirtilmelidir."),
    ]
    with patch("langchain_community.vectorstores.Chroma.from_texts", return_value=mock_vs), \
         patch("langchain_openai.OpenAIEmbeddings"):
        yield mock_vs


class TestLegalStrategyAuditor:
    def _run_auditor(self, state: dict, llm_response_content: str):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=llm_response_content)
        with patch("agents.legalstrategyagent.get_llm", return_value=mock_llm):
            from agents.legalstrategyagent import legal_strategy_auditor
            return legal_strategy_auditor(state)

    def test_report_stored_in_state(self):
        state = {
            "campaign_text": "Masrafsız kredi.",
            "selected_model": "gpt-4o",
            "legal_documents": [],
        }
        content = "Mevzuat İhlalleri: Yok\nFinal Uygunluk Puanı: 90"
        result = self._run_auditor(state, content)
        assert result["legal_audit_report"] == content

    def test_score_parsed_correctly_from_response(self):
        state = {
            "campaign_text": "Kredi kampanyası.",
            "selected_model": "gpt-4o",
            "legal_documents": [],
        }
        content = "Mevzuat İhlalleri: Yok\nRisk Seviyesi: Düşük\nFinal Uygunluk Puanı: 78"
        result = self._run_auditor(state, content)
        assert result["final_score"] == 78

    def test_score_defaults_to_50_when_not_in_response(self):
        state = {
            "campaign_text": "Kampanya metni.",
            "selected_model": "gpt-4o",
            "legal_documents": [],
        }
        content = "Risk Seviyesi: Düşük\nBu yanıtta puan yok."
        result = self._run_auditor(state, content)
        assert result["final_score"] == 50

    def test_score_clamped_to_100_max(self):
        state = {
            "campaign_text": "Kampanya.",
            "selected_model": "gpt-4o",
            "legal_documents": [],
        }
        content = "Final Uygunluk Puanı: 150"
        result = self._run_auditor(state, content)
        assert result["final_score"] == 100

    def test_negative_score_not_parsed_returns_default(self):
        # Regex sadece \d{1,3} yakaladığı için negatif değer eşleşmez → default 50
        state = {
            "campaign_text": "Kampanya.",
            "selected_model": "gpt-4o",
            "legal_documents": [],
        }
        content = "Final Uygunluk Puanı: -10"
        result = self._run_auditor(state, content)
        assert result["final_score"] == 50

    def test_uses_fallback_regulations_when_no_documents(self, mock_chroma_and_embeddings):
        state = {
            "campaign_text": "Kampanya.",
            "selected_model": "gpt-4o",
            "legal_documents": [],
        }
        content = "Final Uygunluk Puanı: 80"
        with patch("agents.llm_factory.get_llm", return_value=MagicMock(
            invoke=MagicMock(return_value=MagicMock(content=content))
        )):
            from agents.legalstrategyagent import legal_strategy_auditor, _fallback_regulations
            legal_strategy_auditor(state)

        call_args = mock_chroma_and_embeddings.from_texts.call_args if hasattr(
            mock_chroma_and_embeddings, "from_texts"
        ) else None
        # Vectorstore oluşturuldu mu kontrol
        from langchain_community.vectorstores import Chroma
        assert Chroma.from_texts.called

    def test_uses_uploaded_documents_when_provided(self, mock_chroma_and_embeddings):
        docs = ["Özel yönetmelik madde 1.", "Özel yönetmelik madde 2."]
        state = {
            "campaign_text": "Kampanya.",
            "selected_model": "gpt-4o",
            "legal_documents": docs,
        }
        content = "Final Uygunluk Puanı: 70"
        with patch("agents.llm_factory.get_llm", return_value=MagicMock(
            invoke=MagicMock(return_value=MagicMock(content=content))
        )):
            from agents.legalstrategyagent import legal_strategy_auditor
            legal_strategy_auditor(state)

        from langchain_community.vectorstores import Chroma
        call_kwargs = Chroma.from_texts.call_args.kwargs if Chroma.from_texts.call_args.kwargs else {}
        call_args = Chroma.from_texts.call_args
        texts_used = call_args[1]["texts"] if call_args[1] else call_args[0][0]
        assert texts_used == docs

    def test_default_model_is_gpt4o(self):
        state = {
            "campaign_text": "Kampanya.",
            "legal_documents": [],
        }
        content = "Final Uygunluk Puanı: 80"
        with patch("agents.legalstrategyagent.get_llm", return_value=MagicMock(
            invoke=MagicMock(return_value=MagicMock(content=content))
        )) as mock_factory:
            from agents.legalstrategyagent import legal_strategy_auditor
            legal_strategy_auditor(state)
            mock_factory.assert_called_once_with("gpt-4o")

    def test_none_legal_documents_treated_as_empty(self):
        state = {
            "campaign_text": "Kampanya.",
            "selected_model": "gpt-4o",
            "legal_documents": None,
        }
        content = "Final Uygunluk Puanı: 85"
        result = self._run_auditor(state, content)
        assert "legal_audit_report" in result


class TestFallbackRegulations:
    def test_fallback_list_is_not_empty(self):
        from agents.legalstrategyagent import _fallback_regulations
        assert len(_fallback_regulations) > 0

    def test_fallback_contains_bddk(self):
        from agents.legalstrategyagent import _fallback_regulations
        combined = " ".join(_fallback_regulations)
        assert "BDDK" in combined

    def test_fallback_contains_tuketici(self):
        from agents.legalstrategyagent import _fallback_regulations
        combined = " ".join(_fallback_regulations)
        assert "Tüketici" in combined or "tüketici" in combined

    def test_all_entries_are_strings(self):
        from agents.legalstrategyagent import _fallback_regulations
        assert all(isinstance(r, str) for r in _fallback_regulations)


class TestLegalAgentStateSchema:
    def test_state_has_required_keys(self):
        from agents.legalstrategyagent import AgentState
        annotations = AgentState.__annotations__
        required = {"campaign_text", "selected_model", "legal_documents", "legal_audit_report", "final_score"}
        assert required.issubset(annotations.keys())
