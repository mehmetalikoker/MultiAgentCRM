# -*- coding: utf-8 -*-
import hashlib
import json
import os
import streamlit as st

_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "user", "users.json")


def _load_raw() -> list:
    if not os.path.exists(_USERS_FILE):
        return []
    with open(_USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("users", [])


def _save_raw(users: list):
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users}, f, ensure_ascii=False, indent=2)


def render():
    st.header("Yönetim Paneli")
    st.markdown("Kullanıcı hesaplarını buradan yönetebilirsiniz.")

    users = _load_raw()

    # ── Mevcut kullanıcılar tablosu ───────────────────────────────────────────
    st.subheader("Mevcut Kullanıcılar")

    if not users:
        st.info("Henüz kullanıcı yok.")
    else:
        for i, u in enumerate(users):
            col_name, col_display, col_delete = st.columns([2, 3, 1])
            with col_name:
                st.markdown(f"**{u['username']}**")
            with col_display:
                st.markdown(u.get("display_name", "—"))
            with col_delete:
                if u["username"] == "admin":
                    st.markdown("<span style='color:#aaa; font-size:0.8rem;'>silinemez</span>",
                                unsafe_allow_html=True)
                else:
                    if st.button("Sil", key=f"del_{i}", type="secondary"):
                        users = [x for x in users if x["username"] != u["username"]]
                        _save_raw(users)
                        st.success(f"'{u['username']}' silindi.")
                        st.rerun()

    st.markdown("---")

    # ── Yeni kullanıcı ekleme formu ───────────────────────────────────────────
    st.subheader("Yeni Kullanıcı Ekle")

    with st.form("add_user_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Kullanıcı Adı")
            new_password = st.text_input("Şifre", type="password")
        with col2:
            new_display = st.text_input("Görünen Ad")
            st.markdown("<br>", unsafe_allow_html=True)

        submitted = st.form_submit_button("Kullanıcı Ekle", type="primary", use_container_width=True)

    if submitted:
        if not new_username.strip() or not new_password.strip():
            st.warning("Kullanıcı adı ve şifre zorunludur.")
        elif any(u["username"] == new_username.strip() for u in users):
            st.error(f"'{new_username}' kullanıcı adı zaten mevcut.")
        else:
            users.append({
                "username": new_username.strip(),
                "password_hash": hashlib.sha256(new_password.encode()).hexdigest(),
                "display_name": new_display.strip() or new_username.strip(),
            })
            _save_raw(users)
            st.success(f"'{new_username}' başarıyla eklendi.")
            st.rerun()
