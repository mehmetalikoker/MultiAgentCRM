# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch


class TestCreateJwt:

    def test_returns_tuple_of_token_and_id(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt
            token, token_id = create_jwt("testuser", "Test User")
            assert isinstance(token, str)
            assert isinstance(token_id, str)

    def test_token_id_is_unique_each_call(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt
            _, tid1 = create_jwt("user", "User")
            _, tid2 = create_jwt("user", "User")
            assert tid1 != tid2

    def test_role_defaults_to_user(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt, verify_jwt
            token, _ = create_jwt("user1", "User One")
            payload = verify_jwt(token)
            assert payload["role"] == "user"

    def test_role_admin_stored_in_token(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt, verify_jwt
            token, _ = create_jwt("admin", "Admin", role="admin")
            payload = verify_jwt(token)
            assert payload["role"] == "admin"

    def test_username_stored_in_sub(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt, verify_jwt
            token, _ = create_jwt("mehmet", "Mehmet")
            payload = verify_jwt(token)
            assert payload["sub"] == "mehmet"

    def test_display_name_stored_in_token(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt, verify_jwt
            token, _ = create_jwt("user", "Mehmet Ali Köker")
            payload = verify_jwt(token)
            assert payload["display_name"] == "Mehmet Ali Köker"

    def test_token_id_stored_in_tid(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt, verify_jwt
            token, token_id = create_jwt("user", "User")
            payload = verify_jwt(token)
            assert payload["tid"] == token_id

    def test_missing_jwt_secret_raises_runtime_error(self):
        with patch.dict("os.environ", {"JWT_SECRET": ""}):
            import importlib
            import user.jwt_auth as jwt_mod
            importlib.reload(jwt_mod)
            with pytest.raises(RuntimeError, match="JWT_SECRET"):
                jwt_mod._secret()


class TestVerifyJwt:

    def test_valid_token_returns_payload(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt, verify_jwt
            token, _ = create_jwt("user", "User")
            payload = verify_jwt(token)
            assert payload is not None

    def test_invalid_token_returns_none(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import verify_jwt
            assert verify_jwt("invalid.token.here") is None

    def test_tampered_token_returns_none(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import create_jwt, verify_jwt
            token, _ = create_jwt("user", "User")
            tampered = token[:-5] + "XXXXX"
            assert verify_jwt(tampered) is None

    def test_wrong_secret_returns_none(self):
        with patch.dict("os.environ", {"JWT_SECRET": "secret-a"}):
            from user.jwt_auth import create_jwt
            import importlib, user.jwt_auth as m
            importlib.reload(m)
            token, _ = m.create_jwt("user", "User")

        with patch.dict("os.environ", {"JWT_SECRET": "secret-b"}):
            importlib.reload(m)
            assert m.verify_jwt(token) is None

    def test_empty_string_returns_none(self):
        with patch.dict("os.environ", {"JWT_SECRET": "test-secret"}):
            from user.jwt_auth import verify_jwt
            assert verify_jwt("") is None
