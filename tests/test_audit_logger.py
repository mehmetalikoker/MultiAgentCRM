# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_col():
    col = MagicMock()
    with patch("agents.audit_logger._col", return_value=col):
        yield col


class TestLogAudit:
    """
    log_audit(**kwargs) fonksiyonunu test eder.

    Her denetim işlemi sonrasında (metin, görsel, hukuk) çağrılır ve sonucu
    MongoDB audit_logs collection'ına kaydeder. Geçmiş ve istatistik sekmeleri
    bu verileri okur.

    Test edilen senaryolar:
    - Her çağrıda tam olarak bir döküman insert edilmesi
    - Timestamp alanının kaydedilmesi
    - username alanının doğru kaydedilmesi
    - Uzun campaign_text'in 200 karaktere kırpılması
    - Uzun result_summary'nin 3000 karaktere kırpılması
    - is_safe belirtilmediğinde None olarak kaydedilmesi
    - score ve channel alanlarının kaydedilmesi
    """

    def test_insert_called_once(self, mock_col):
        from agents.audit_logger import log_audit
        log_audit(username="ali", agent="compliance", model="gpt-4o",
                  campaign_text="Kampanya", is_safe=True)
        mock_col.insert_one.assert_called_once()

    def test_timestamp_is_stored(self, mock_col):
        from agents.audit_logger import log_audit
        log_audit(username="ali", agent="compliance", model="gpt-4o",
                  campaign_text="Kampanya")
        doc = mock_col.insert_one.call_args[0][0]
        assert "timestamp" in doc

    def test_username_stored(self, mock_col):
        from agents.audit_logger import log_audit
        log_audit(username="mehmet", agent="legal", model="gpt-4o",
                  campaign_text="Kampanya")
        doc = mock_col.insert_one.call_args[0][0]
        assert doc["username"] == "mehmet"

    def test_campaign_text_truncated_to_200(self, mock_col):
        from agents.audit_logger import log_audit
        long_text = "x" * 500
        log_audit(username="u", agent="compliance", model="m", campaign_text=long_text)
        doc = mock_col.insert_one.call_args[0][0]
        assert len(doc["campaign_text_preview"]) == 200

    def test_result_summary_truncated_to_3000(self, mock_col):
        from agents.audit_logger import log_audit
        long_summary = "s" * 5000
        log_audit(username="u", agent="compliance", model="m",
                  campaign_text="x", result_summary=long_summary)
        doc = mock_col.insert_one.call_args[0][0]
        assert len(doc["result_summary"]) == 3000

    def test_is_safe_none_by_default(self, mock_col):
        from agents.audit_logger import log_audit
        log_audit(username="u", agent="legal", model="m", campaign_text="x")
        doc = mock_col.insert_one.call_args[0][0]
        assert doc["is_safe"] is None

    def test_score_stored(self, mock_col):
        from agents.audit_logger import log_audit
        log_audit(username="u", agent="legal", model="m",
                  campaign_text="x", score=85)
        doc = mock_col.insert_one.call_args[0][0]
        assert doc["score"] == 85

    def test_channel_stored(self, mock_col):
        from agents.audit_logger import log_audit
        log_audit(username="u", agent="compliance", model="m",
                  campaign_text="x", channel="SMS")
        doc = mock_col.insert_one.call_args[0][0]
        assert doc["channel"] == "SMS"


class TestLoadAuditLog:
    """
    load_audit_log() fonksiyonunu test eder.

    MongoDB audit_logs collection'ından tüm kayıtları timestamp'e göre
    azalan sırada (en yeni önce) liste olarak döndürür. Geçmiş sekmesi
    ve istatistik hesaplamaları bu fonksiyonu kullanır.

    Test edilen senaryolar:
    - Dönen değerin liste olması
    - Kayıtların timestamp'e göre azalan sırada getirilmesi
    - _id alanının sonuçlardan hariç tutulması (güvenlik ve serileştirme)
    """

    def test_returns_list(self, mock_col):
        mock_col.find.return_value.sort.return_value = [
            {"username": "ali", "agent": "compliance"}
        ]
        from agents.audit_logger import load_audit_log
        result = load_audit_log()
        assert isinstance(result, list)

    def test_sorted_by_timestamp_descending(self, mock_col):
        mock_col.find.return_value.sort.return_value = []
        from agents.audit_logger import load_audit_log
        load_audit_log()
        mock_col.find.return_value.sort.assert_called_once_with("timestamp", -1)

    def test_id_field_excluded(self, mock_col):
        mock_col.find.return_value.sort.return_value = []
        from agents.audit_logger import load_audit_log
        load_audit_log()
        find_kwargs = mock_col.find.call_args[0]
        assert find_kwargs[1] == {"_id": 0}
