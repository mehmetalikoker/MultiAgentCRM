# -*- coding: utf-8 -*-
import pytest
from collections import Counter
from ui.tab_istatistik import (
    get_agent_label,
    compute_summary,
    compute_agent_counts,
    compute_model_counts,
    compute_user_stats,
)


# ── Yardımcı sabitler ─────────────────────────────────────────────────────────

def _entry(username="user1", agent="compliance", model="claude-sonnet-4-6",
           is_safe=True, channel=None):
    return {
        "username": username,
        "agent":    agent,
        "model":    model,
        "is_safe":  is_safe,
        "channel":  channel,
    }


# ─────────────────────────────────────────────────────────────────────────────
class TestGetAgentLabel:

    def test_compliance_returns_turkish_label(self):
        assert get_agent_label("compliance") == "Metin Denetimi"

    def test_visual_returns_turkish_label(self):
        assert get_agent_label("visual") == "Görsel Denetim"

    def test_legal_returns_turkish_label(self):
        assert get_agent_label("legal") == "Hukuk & Strateji"

    def test_unknown_agent_returns_key_as_fallback(self):
        assert get_agent_label("unknown_agent") == "unknown_agent"

    def test_empty_string_returns_empty(self):
        assert get_agent_label("") == ""


# ─────────────────────────────────────────────────────────────────────────────
class TestComputeSummary:

    def test_empty_logs_returns_zeros(self):
        result = compute_summary([])
        assert result == {"total": 0, "safe": 0, "unsafe": 0, "safe_rate": 0}

    def test_total_count(self):
        logs = [_entry(is_safe=True)] * 3 + [_entry(is_safe=False)] * 2
        assert compute_summary(logs)["total"] == 5

    def test_safe_count(self):
        logs = [_entry(is_safe=True)] * 4 + [_entry(is_safe=False)]
        assert compute_summary(logs)["safe"] == 4

    def test_unsafe_count(self):
        logs = [_entry(is_safe=True)] * 2 + [_entry(is_safe=False)] * 3
        assert compute_summary(logs)["unsafe"] == 3

    def test_safe_rate_full(self):
        logs = [_entry(is_safe=True)] * 10
        assert compute_summary(logs)["safe_rate"] == 100

    def test_safe_rate_zero(self):
        logs = [_entry(is_safe=False)] * 5
        assert compute_summary(logs)["safe_rate"] == 0

    def test_safe_rate_rounded(self):
        # 1 safe, 2 unsafe → %33
        logs = [_entry(is_safe=True)] + [_entry(is_safe=False)] * 2
        assert compute_summary(logs)["safe_rate"] == 33

    def test_none_is_safe_not_counted_as_safe_or_unsafe(self):
        logs = [_entry(is_safe=None), _entry(is_safe=True), _entry(is_safe=False)]
        result = compute_summary(logs)
        assert result["safe"]   == 1
        assert result["unsafe"] == 1
        assert result["total"]  == 3

    def test_all_none_is_safe_returns_zero_rate(self):
        logs = [_entry(is_safe=None)] * 3
        assert compute_summary(logs)["safe_rate"] == 0


# ─────────────────────────────────────────────────────────────────────────────
class TestComputeAgentCounts:

    def test_empty_logs_returns_empty_counter(self):
        assert compute_agent_counts([]) == Counter()

    def test_single_agent_counted(self):
        logs = [_entry(agent="compliance")] * 3
        counts = compute_agent_counts(logs)
        assert counts["compliance"] == 3

    def test_multiple_agents_counted_separately(self):
        logs = (
            [_entry(agent="compliance")] * 2 +
            [_entry(agent="visual")] +
            [_entry(agent="legal")] * 3
        )
        counts = compute_agent_counts(logs)
        assert counts["compliance"] == 2
        assert counts["visual"]     == 1
        assert counts["legal"]      == 3

    def test_missing_agent_key_falls_back_to_dash(self):
        logs = [{"username": "u", "model": "m", "is_safe": True}]
        counts = compute_agent_counts(logs)
        assert counts["—"] == 1

    def test_most_common_order(self):
        logs = [_entry(agent="legal")] * 5 + [_entry(agent="compliance")] * 2
        most_common = compute_agent_counts(logs).most_common()
        assert most_common[0][0] == "legal"


# ─────────────────────────────────────────────────────────────────────────────
class TestComputeModelCounts:

    def test_empty_logs_returns_empty_counter(self):
        assert compute_model_counts([]) == Counter()

    def test_single_model_counted(self):
        logs = [_entry(model="claude-sonnet-4-6")] * 4
        assert compute_model_counts(logs)["claude-sonnet-4-6"] == 4

    def test_multiple_models_counted(self):
        logs = (
            [_entry(model="claude-sonnet-4-6")] * 3 +
            [_entry(model="gpt-4-turbo")] * 2
        )
        counts = compute_model_counts(logs)
        assert counts["claude-sonnet-4-6"] == 3
        assert counts["gpt-4-turbo"]       == 2

    def test_missing_model_key_falls_back_to_dash(self):
        logs = [{"username": "u", "agent": "compliance", "is_safe": True}]
        counts = compute_model_counts(logs)
        assert counts["—"] == 1

    def test_most_common_order(self):
        logs = [_entry(model="deepseek-chat")] * 7 + [_entry(model="gpt-4-turbo")] * 1
        most_common = compute_model_counts(logs).most_common()
        assert most_common[0][0] == "deepseek-chat"


# ─────────────────────────────────────────────────────────────────────────────
class TestComputeUserStats:

    def test_empty_logs_returns_empty_counters(self):
        stats = compute_user_stats([])
        assert stats["total"]  == Counter()
        assert stats["safe"]   == Counter()
        assert stats["unsafe"] == Counter()

    def test_total_per_user(self):
        logs = [_entry(username="ali")] * 3 + [_entry(username="veli")] * 2
        stats = compute_user_stats(logs)
        assert stats["total"]["ali"]  == 3
        assert stats["total"]["veli"] == 2

    def test_safe_per_user(self):
        logs = (
            [_entry(username="ali", is_safe=True)]  * 2 +
            [_entry(username="ali", is_safe=False)] +
            [_entry(username="veli", is_safe=True)]
        )
        stats = compute_user_stats(logs)
        assert stats["safe"]["ali"]  == 2
        assert stats["safe"]["veli"] == 1

    def test_unsafe_per_user(self):
        logs = (
            [_entry(username="ali", is_safe=False)] * 3 +
            [_entry(username="veli", is_safe=False)]
        )
        stats = compute_user_stats(logs)
        assert stats["unsafe"]["ali"]  == 3
        assert stats["unsafe"]["veli"] == 1

    def test_user_with_no_safe_entries_not_in_safe_counter(self):
        logs = [_entry(username="ali", is_safe=False)] * 2
        stats = compute_user_stats(logs)
        assert stats["safe"]["ali"] == 0  # Counter default

    def test_user_with_no_unsafe_entries_not_in_unsafe_counter(self):
        logs = [_entry(username="ali", is_safe=True)] * 2
        stats = compute_user_stats(logs)
        assert stats["unsafe"]["ali"] == 0  # Counter default

    def test_none_is_safe_not_in_safe_or_unsafe(self):
        logs = [_entry(username="ali", is_safe=None)]
        stats = compute_user_stats(logs)
        assert "ali" not in stats["safe"]
        assert "ali" not in stats["unsafe"]
        assert stats["total"]["ali"] == 1

    def test_sorted_by_total_descending(self):
        logs = (
            [_entry(username="az_kullanan")] +
            [_entry(username="cok_kullanan")] * 5
        )
        stats = compute_user_stats(logs)
        sorted_users = sorted(stats["total"], key=lambda u: -stats["total"][u])
        assert sorted_users[0] == "cok_kullanan"

    def test_multiple_users_all_tracked(self):
        users = ["ali", "veli", "ayse", "fatma"]
        logs = [_entry(username=u) for u in users]
        stats = compute_user_stats(logs)
        for u in users:
            assert stats["total"][u] == 1
