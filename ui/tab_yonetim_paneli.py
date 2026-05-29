# -*- coding: utf-8 -*-
import streamlit as st
from user.db import load_users_list, add_user, delete_user, unlock_user, set_user_email, set_user_role


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
            current_email = u.get("email", "")

            role = u.get("role", "user")
            role_icon = "👑 " if role == "admin" else ""
            with st.expander(
                f"{'🔒 ' if is_locked else ''}{role_icon}{u['username']} — {u.get('display_name', '')}",
                expanded=False,
            ):
                col_info, col_actions = st.columns([3, 1])

                with col_info:
                    with st.form(key=f"email_form_{i}"):
                        typed_email = st.text_input(
                            "E-posta Adresi",
                            value=current_email,
                            placeholder="eposta@sirket.com",
                        )
                        save = st.form_submit_button("E-postayı Kaydet", type="primary")

                    if save:
                        typed_email = typed_email.strip().lower()
                        # Duplicate kontrol (başka kullanıcıda aynı mail var mı?)
                        all_users = load_users_list()
                        duplicate = any(
                            v.get("email", "").lower() == typed_email
                            and v["username"] != u["username"]
                            for v in all_users
                            if typed_email
                        )
                        if duplicate:
                            st.error(f"'{typed_email}' adresi başka bir kullanıcıya zaten atanmış.")
                        else:
                            set_user_email(u["username"], typed_email)
                            st.success("E-posta güncellendi.")
                            st.rerun()

                with col_actions:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

                    current_user = st.session_state.get("username", "")
                    new_role = "user" if role == "admin" else "admin"
                    role_btn_label = "👑 Admin Yap" if role == "user" else "👤 Kullanıcı Yap"
                    if u["username"] != current_user:
                        if st.button(role_btn_label, key=f"role_{i}", use_container_width=True):
                            set_user_role(u["username"], new_role)
                            st.success(f"'{u['username']}' rolü '{new_role}' olarak güncellendi.")
                            st.rerun()

                    if is_locked:
                        if st.button("Aktif Et", key=f"unlock_{i}", type="primary",
                                     use_container_width=True):
                            unlock_user(u["username"])
                            st.success(f"'{u['username']}' hesabı aktif edildi.")
                            st.rerun()
                    if u["username"] != current_user:
                        if st.button("Sil", key=f"del_{i}", type="secondary",
                                     use_container_width=True):
                            delete_user(u["username"])
                            st.success(f"'{u['username']}' silindi.")
                            st.rerun()
                    else:
                        st.markdown("<span style='color:#aaa; font-size:0.8rem;'>kendi hesabın</span>",
                                    unsafe_allow_html=True)

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
            new_email = st.text_input("E-posta Adresi", placeholder="eposta@sirket.com")
        new_role = st.selectbox("Rol", options=["user", "admin"],
                                format_func=lambda r: "👤 Kullanıcı" if r == "user" else "👑 Admin")

        submitted = st.form_submit_button("Kullanıcı Ekle", type="primary", use_container_width=True)

    if submitted:
        if not new_username.strip() or not new_password.strip():
            st.warning("Kullanıcı adı ve şifre zorunludur.")
        elif any(u["username"] == new_username.strip() for u in users):
            st.error(f"'{new_username}' kullanıcı adı zaten mevcut.")
        elif new_email.strip() and any(
            u.get("email", "").lower() == new_email.strip().lower() for u in users
        ):
            st.error(f"'{new_email.strip()}' e-posta adresi zaten kullanımda.")
        else:
            add_user(new_username.strip(), new_password, new_display.strip(), new_email.strip(), new_role)
            st.success(f"'{new_username}' başarıyla eklendi.")
            st.rerun()
