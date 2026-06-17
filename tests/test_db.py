# -*- coding: utf-8 -*-
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_col():
    col = MagicMock()
    with patch("user.db._col", return_value=col):
        yield col


class TestLoadUsers:
    """
    load_users() fonksiyonunu test eder.

    MongoDB users collection'ındaki tüm kullanıcıları username'e göre
    indekslenmiş dict olarak döndürür. Kimlik doğrulama sırasında
    kullanıcı arama için kullanılır.

    Test edilen senaryolar:
    - Kullanıcıların username anahtarıyla dict'e dönüştürülmesi
    - Boş collection için boş dict döndürülmesi
    """

    def test_returns_dict_keyed_by_username(self, mock_col):
        mock_col.find.return_value = [
            {"username": "ali", "role": "user"},
            {"username": "admin", "role": "admin"},
        ]
        from user.db import load_users
        result = load_users()
        assert "ali" in result
        assert "admin" in result

    def test_empty_collection_returns_empty_dict(self, mock_col):
        mock_col.find.return_value = []
        from user.db import load_users
        assert load_users() == {}


class TestLoadUsersList:
    """
    load_users_list() fonksiyonunu test eder.

    MongoDB users collection'ındaki tüm kullanıcıları liste olarak döndürür.
    Yönetim panelinde kullanıcı listesi göstermek için kullanılır.

    Test edilen senaryolar:
    - Dönen değerin liste olması
    - Tüm kullanıcıların listede yer alması
    - Boş collection için boş liste döndürülmesi
    """

    def test_returns_list(self, mock_col):
        mock_col.find.return_value = [{"username": "ali"}, {"username": "veli"}]
        from user.db import load_users_list
        result = load_users_list()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_empty_collection_returns_empty_list(self, mock_col):
        mock_col.find.return_value = []
        from user.db import load_users_list
        assert load_users_list() == []


class TestAddUser:
    """
    add_user(username, password, display_name, email, role) fonksiyonunu test eder.

    Yeni kullanıcıyı MongoDB users collection'ına ekler. Şifre hiçbir zaman
    düz metin olarak saklanmaz; SHA-256 hash'i kaydedilir. E-posta opsiyoneldir.

    Test edilen senaryolar:
    - insert_one'ın doğru username ile çağrılması
    - Şifrenin SHA-256 hash'i olarak saklanması (düz metin değil)
    - Rol belirtilmediğinde varsayılan "user" rolünün kaydedilmesi
    - "admin" rolünün doğru kaydedilmesi
    - E-posta adresinin küçük harfe dönüştürülerek saklanması
    - Boş e-posta için "email" alanının eklenmemesi
    - display_name boş geldiğinde username'in kullanılması
    """

    def test_insert_called_with_username(self, mock_col):
        from user.db import add_user
        add_user("testuser", "pass123", "Test User")
        call_args = mock_col.insert_one.call_args[0][0]
        assert call_args["username"] == "testuser"

    def test_password_is_hashed(self, mock_col):
        import hashlib
        from user.db import add_user
        add_user("user", "mypassword", "User")
        call_args = mock_col.insert_one.call_args[0][0]
        expected = hashlib.sha256("mypassword".encode()).hexdigest()
        assert call_args["password_hash"] == expected

    def test_default_role_is_user(self, mock_col):
        from user.db import add_user
        add_user("user", "pass", "User")
        call_args = mock_col.insert_one.call_args[0][0]
        assert call_args["role"] == "user"

    def test_admin_role_stored(self, mock_col):
        from user.db import add_user
        add_user("admin2", "pass", "Admin", role="admin")
        call_args = mock_col.insert_one.call_args[0][0]
        assert call_args["role"] == "admin"

    def test_email_stored_lowercase(self, mock_col):
        from user.db import add_user
        add_user("user", "pass", "User", email="USER@TEST.COM")
        call_args = mock_col.insert_one.call_args[0][0]
        assert call_args["email"] == "user@test.com"

    def test_empty_email_not_stored(self, mock_col):
        from user.db import add_user
        add_user("user", "pass", "User", email="")
        call_args = mock_col.insert_one.call_args[0][0]
        assert "email" not in call_args

    def test_display_name_falls_back_to_username(self, mock_col):
        from user.db import add_user
        add_user("user", "pass", "")
        call_args = mock_col.insert_one.call_args[0][0]
        assert call_args["display_name"] == "user"


class TestActiveToken:
    """
    set/get/clear_active_token fonksiyonlarını test eder.

    Tek aktif oturum mekanizmasının MongoDB tarafındaki katmanıdır.
    Her girişte yeni token_id kaydedilir; başka cihazdan giriş yapıldığında
    eski token_id geçersiz kalır ve o kullanıcı otomatik çıkış yapar.

    Test edilen senaryolar:
    - set_active_token'ın update_one çağırması
    - get_active_token'ın token_id değerini döndürmesi
    - Kullanıcı bulunamazsa get_active_token'ın None döndürmesi
    - clear_active_token'ın $unset operatörü kullanması
    """

    def test_set_active_token_calls_update(self, mock_col):
        from user.db import set_active_token
        set_active_token("user", "token-id-123")
        mock_col.update_one.assert_called_once()

    def test_get_active_token_returns_value(self, mock_col):
        mock_col.find_one.return_value = {"active_token_id": "abc-123"}
        from user.db import get_active_token
        result = get_active_token("user")
        assert result == "abc-123"

    def test_get_active_token_returns_none_when_user_not_found(self, mock_col):
        mock_col.find_one.return_value = None
        from user.db import get_active_token
        result = get_active_token("nonexistent")
        assert result is None

    def test_clear_active_token_calls_unset(self, mock_col):
        from user.db import clear_active_token
        clear_active_token("user")
        call_args = mock_col.update_one.call_args[0]
        assert "$unset" in call_args[1]


class TestLockUnlock:
    """
    lock_user() ve unlock_user() fonksiyonlarını test eder.

    5 başarısız giriş denemesinde hesap kilitlenir (rate_limiter tarafından tetiklenir).
    Admin, yönetim panelinden hesabı tekrar aktif edebilir.

    Test edilen senaryolar:
    - lock_user'ın MongoDB'de locked:True ayarlaması
    - unlock_user'ın MongoDB'de locked alanını kaldırması ($unset)
    """

    def test_lock_user_sets_locked_true(self, mock_col):
        from user.db import lock_user
        lock_user("user")
        call_args = mock_col.update_one.call_args[0]
        assert call_args[1]["$set"]["locked"] is True

    def test_unlock_user_unsets_locked(self, mock_col):
        from user.db import unlock_user
        unlock_user("user")
        call_args = mock_col.update_one.call_args[0]
        assert "locked" in call_args[1]["$unset"]


class TestUpdatePassword:
    """
    update_password(username, new_password) fonksiyonunu test eder.

    Kullanıcının şifresini SHA-256 hash'i olarak günceller.
    Şifre sıfırlama akışında consume_token sonrasında çağrılır.

    Test edilen senaryolar:
    - Yeni şifrenin SHA-256 hash'inin kaydedilmesi (düz metin değil)
    - Doğru kullanıcının güncellenmesi
    """

    def test_new_password_is_hashed(self, mock_col):
        import hashlib
        from user.db import update_password
        update_password("user", "newpassword")
        call_args = mock_col.update_one.call_args[0]
        expected = hashlib.sha256("newpassword".encode()).hexdigest()
        assert call_args[1]["$set"]["password_hash"] == expected

    def test_correct_user_targeted(self, mock_col):
        from user.db import update_password
        update_password("targetuser", "pass")
        call_args = mock_col.update_one.call_args[0]
        assert call_args[0]["username"] == "targetuser"


class TestGetUserByEmail:
    """
    get_user_by_email(email) fonksiyonunu test eder.

    Şifre sıfırlama akışında e-posta adresine göre kullanıcıyı bulur.
    Kullanıcı bulunamazsa None döndürür.

    Test edilen senaryolar:
    - Kullanıcı bulunduğunda dökümanın döndürülmesi
    - Kullanıcı bulunamazsa None döndürülmesi
    - E-posta adresinin küçük harfe dönüştürülerek sorgulanması
    """

    def test_returns_user_when_found(self, mock_col):
        mock_col.find_one.return_value = {"username": "ali", "email": "ali@test.com"}
        from user.db import get_user_by_email
        result = get_user_by_email("ali@test.com")
        assert result["username"] == "ali"

    def test_returns_none_when_not_found(self, mock_col):
        mock_col.find_one.return_value = None
        from user.db import get_user_by_email
        assert get_user_by_email("unknown@test.com") is None

    def test_email_lowercased_in_query(self, mock_col):
        mock_col.find_one.return_value = None
        from user.db import get_user_by_email
        get_user_by_email("ALI@TEST.COM")
        call_args = mock_col.find_one.call_args[0][0]
        assert call_args["email"] == "ali@test.com"


class TestSetUserEmail:
    """
    set_user_email(username, email) fonksiyonunu test eder.

    Yönetim panelinden kullanıcıya e-posta adresi atamak veya güncellemek için
    kullanılır. E-posta küçük harfe dönüştürülerek saklanır.

    Test edilen senaryolar:
    - E-posta adresinin küçük harfe dönüştürülerek kaydedilmesi
    - Doğru kullanıcının hedeflenmesi
    """

    def test_email_stored_lowercase(self, mock_col):
        from user.db import set_user_email
        set_user_email("user", "USER@TEST.COM")
        call_args = mock_col.update_one.call_args[0]
        assert call_args[1]["$set"]["email"] == "user@test.com"

    def test_correct_user_targeted(self, mock_col):
        from user.db import set_user_email
        set_user_email("targetuser", "a@b.com")
        call_args = mock_col.update_one.call_args[0]
        assert call_args[0]["username"] == "targetuser"


class TestDeleteUser:
    """
    delete_user(username) fonksiyonunu test eder.

    Yönetim panelinden kullanıcıyı MongoDB'den siler.
    Admin hesabının silinmesi UI katmanında engellenir; bu fonksiyon sadece
    silme işlemini gerçekleştirir.

    Test edilen senaryolar:
    - delete_one'ın çağrılması
    - Doğru kullanıcının hedeflenmesi
    """

    def test_delete_user_calls_delete_one(self, mock_col):
        from user.db import delete_user
        delete_user("ali")
        mock_col.delete_one.assert_called_once()

    def test_delete_user_targets_correct_username(self, mock_col):
        from user.db import delete_user
        delete_user("ali")
        call_args = mock_col.delete_one.call_args[0][0]
        assert call_args["username"] == "ali"


class TestSetUserRole:
    """
    set_user_role(username, role) fonksiyonunu test eder.

    Yönetim panelinden kullanıcının rolünü "admin" veya "user" olarak günceller.
    Rol değişikliği anında MongoDB'ye yazılır; bir sonraki girişte JWT'ye yansır.

    Test edilen senaryolar:
    - Kullanıcıya "admin" rolü atanması
    - Kullanıcıdan "admin" rolünün alınıp "user" yapılması
    """

    def test_set_user_role_admin(self, mock_col):
        from user.db import set_user_role
        set_user_role("user", "admin")
        call_args = mock_col.update_one.call_args[0]
        assert call_args[1]["$set"]["role"] == "admin"

    def test_set_user_role_user(self, mock_col):
        from user.db import set_user_role
        set_user_role("admin", "user")
        call_args = mock_col.update_one.call_args[0]
        assert call_args[1]["$set"]["role"] == "user"
