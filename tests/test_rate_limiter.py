# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone


@pytest.fixture
def mock_col():
    col = MagicMock()
    with patch("user.rate_limiter._col", return_value=col):
        yield col


class TestRecordFailure:

    def test_inserts_attempt_document(self, mock_col):
        mock_col.count_documents.return_value = 1
        from user.rate_limiter import record_failure
        record_failure("testuser")
        mock_col.insert_one.assert_called_once()

    def test_inserted_document_has_username_lowercase(self, mock_col):
        mock_col.count_documents.return_value = 1
        from user.rate_limiter import record_failure
        record_failure("TestUser")
        doc = mock_col.insert_one.call_args[0][0]
        assert doc["username"] == "testuser"

    def test_inserted_document_has_created_at(self, mock_col):
        mock_col.count_documents.return_value = 1
        from user.rate_limiter import record_failure
        record_failure("user")
        doc = mock_col.insert_one.call_args[0][0]
        assert "created_at" in doc

    def test_returns_false_when_below_limit(self, mock_col):
        mock_col.count_documents.return_value = 3
        from user.rate_limiter import record_failure
        result = record_failure("user")
        assert result is False

    def test_returns_true_when_limit_reached(self, mock_col):
        mock_col.count_documents.return_value = 5
        with patch("user.rate_limiter._col", return_value=mock_col), \
             patch("user.db.lock_user") as mock_lock:
            from user.rate_limiter import record_failure
            result = record_failure("user")
        assert result is True

    def test_lock_called_when_limit_reached(self, mock_col):
        mock_col.count_documents.return_value = 5
        with patch("user.rate_limiter._col", return_value=mock_col), \
             patch("user.db.lock_user") as mock_lock:
            from user.rate_limiter import record_failure
            record_failure("lockme")
            mock_lock.assert_called_once_with("lockme")

    def test_attempts_deleted_when_limit_reached(self, mock_col):
        mock_col.count_documents.return_value = 5
        with patch("user.rate_limiter._col", return_value=mock_col), \
             patch("user.db.lock_user"):
            from user.rate_limiter import record_failure
            record_failure("user")
            mock_col.delete_many.assert_called_once()


class TestRecordSuccess:

    def test_deletes_all_attempts_for_user(self, mock_col):
        from user.rate_limiter import record_success
        record_success("TestUser")
        mock_col.delete_many.assert_called_once()
        call_args = mock_col.delete_many.call_args[0][0]
        assert call_args["username"] == "testuser"


class TestAttemptsRemaining:

    def test_returns_max_minus_count(self, mock_col):
        mock_col.count_documents.return_value = 2
        from user.rate_limiter import attempts_remaining
        assert attempts_remaining("user") == 3

    def test_returns_zero_when_at_limit(self, mock_col):
        mock_col.count_documents.return_value = 5
        from user.rate_limiter import attempts_remaining
        assert attempts_remaining("user") == 0

    def test_returns_zero_when_over_limit(self, mock_col):
        mock_col.count_documents.return_value = 10
        from user.rate_limiter import attempts_remaining
        assert attempts_remaining("user") == 0

    def test_username_lowercased_in_query(self, mock_col):
        mock_col.count_documents.return_value = 0
        from user.rate_limiter import attempts_remaining
        attempts_remaining("UPPERCASE")
        call_args = mock_col.count_documents.call_args[0][0]
        assert call_args["username"] == "uppercase"
