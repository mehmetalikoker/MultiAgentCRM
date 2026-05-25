# -*- coding: utf-8 -*-
import streamlit as st
from user.db import load_users_list, add_user, delete_user, unlock_user


def render():
    st.header("Yönetim Paneli")
    st.markdown("Kullanıcı hesaplarını buradan yönetebilirsiniz.")

    users = load_users_list()

    # ── Mevcut kullanıcılar tablosu ───────────────────────────────────────────
    st.subheader("Mevcut Kullanıcılar")

    if not users:
        st.info("Henüz kullanıcı yok.")
    else:
        for i, u in enumerate(users):
            is_locked = u.get("locked", False)
            col_name, col_display, col_unlock, col_delete = st.columns([2, 3, 1, 1])
            with col_name:
                if is_locked:
                    st.markdown(
                        f"**{u['username']}** "
                        "<span style='background:#d32f2f;color:#fff;border-radius:4px;"
                        "padding:1px 7px;font-size:0.75rem;'>KİLİTLİ</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"**{u['username']}**")
            with col_display:
                st.markdown(u.get("display_name", "—"))
            with col_unlock:
                if is_locked:
                    if st.button("Aktif Et", key=f"unlock_{i}", type="primary"):
                        unlock_user(u["username"])
                        st.success(f"'{u['username']}' hesabı aktif edildi.")
                        st.rerun()
            with col_delete:
                if u["username"] == "admin":
                    st.markdown("<span style='color:#aaa; font-size:0.8rem;'>silinemez</span>",
                                unsafe_allow_html=True)
                else:
                    if st.button("Sil", key=f"del_{i}", type="secondary"):
                        delete_user(u["username"])
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
            add_user(new_username.strip(), new_password, new_display.strip())
            st.success(f"'{new_username}' başarıyla eklendi.")
            st.rerun()
