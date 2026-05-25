# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import hashlib
import streamlit as st

st.set_page_config(
    page_title="Kampanya Denetim Sistemi",
    page_icon="🏦",
    layout="wide"
)

# ─── ING MARKA TEMASı ─────────────────────────────────────────────────────────
def _load_css(path: str) -> None:
    _base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_base, path), encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

_load_css("css/main.css")

# ─── KİMLİK DOĞRULAMA ─────────────────────────────────────────────────────────

from user.db import load_users
from user.rate_limiter import record_failure, record_success, attempts_remaining


def _check_credentials(username: str, password: str) -> bool:
    users = load_users()
    user = users.get(username)
    if not user:
        return False
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return hashed == user["password_hash"]


def _show_login():
    col_left, col_center, col_right = st.columns([1, 1.1, 1])
    with col_center:
        st.markdown("""
        <div class="ing-login-card">
            <div class="ing-login-title"><span style="color:#FF6200;">Agentic CRM</span></div>
            <div class="ing-login-sub">Devam etmek için kurumsal hesabınızla giriş yapın</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='background:#fff; border-radius:0 0 12px 12px; padding:0 36px 32px; "
                    "box-shadow:0 4px 24px rgba(0,0,0,0.10); margin-top:-8px;'>",
                    unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            username = st.text_input("Kullanıcı Adı", placeholder="kullanıcı adı")
            password = st.text_input("Şifre", type="password", placeholder="••••••••")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Giriş Yap", use_container_width=True, type="primary")

        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            users = load_users()
            user_record = users.get(username)
            if user_record and user_record.get("locked"):
                st.error("Hesabınız kilitlenmiştir. Lütfen yönetici ile iletişime geçin.")
            elif _check_credentials(username, password):
                record_success(username)
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["display_name"] = user_record.get("display_name", username)
                st.rerun()
            else:
                locked_now = record_failure(username)
                if locked_now:
                    st.error(
                        "Çok fazla başarısız giriş denemesi. "
                        "Hesabınız kilitlendi. Lütfen yönetici ile iletişime geçin."
                    )
                else:
                    remaining = attempts_remaining(username)
                    if remaining <= 2:
                        st.warning(
                            f"Kullanıcı adı veya şifre hatalı. "
                            f"{remaining} deneme hakkınız kaldı."
                        )
                    else:
                        st.error("Kullanıcı adı veya şifre hatalı.")


if not st.session_state.get("authenticated"):
    _show_login()
    st.stop()

MODELS = {
    # Anthropic
    "claude-opus-4-7":           "Claude Opus 4.7",
    "claude-sonnet-4-6":         "Claude Sonnet 4.6",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    
    # OpenAI
    # "gpt-4o":                    "GPT-4o",
    # "gpt-4o-mini":               "GPT-4o Mini",
    "gpt-4-turbo":               "GPT-4 Turbo",
    # "gpt-3.5-turbo":             "GPT-3.5 Turbo",
    
    # Google Gemini
    # "gemini-2.0-flash":            "Gemini 2.0 Flash",
    # "gemini-2.0-flash-lite":       "Gemini 2.0 Flash Lite",
    # "gemini-1.5-pro-latest":       "Gemini 1.5 Pro",
    
    # DeepSeek
    "deepseek-chat":             "DeepSeek Chat",
}

# Görsel denetimi desteklemeyen modeller
_NON_VISION_MODELS = {"gpt-3.5-turbo", "deepseek-chat"}

with st.sidebar:
    st.markdown("---")
    display_name = st.session_state.get("display_name", st.session_state.get("username", ""))
    st.markdown(f"<span style='font-size:0.85rem;color:#ccc;'>👤 {display_name} olarak giriş yapıldı</span>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("Çıkış Yap", use_container_width=True, type="secondary"):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    st.header("⚙️ Model Ayarları")
    selected_model = st.selectbox(
        "LLM Modeli",
        options=list(MODELS.keys()),
        format_func=lambda k: MODELS[k],
        index=0,
    )
    st.caption(f"Seçili model tüm denetim adımlarında kullanılır.")
    if selected_model in _NON_VISION_MODELS:
        st.warning("⚠️ Seçili model görsel denetimi desteklemiyor.")

    st.markdown("---")
st.markdown(
    "<h1 style='color:#FF6200; font-size:2.4rem; border-bottom: 3px solid #FF6200; "
    "padding-bottom:10px; display:block;'>Agentic CRM</h1>",
    unsafe_allow_html=True
)
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

is_admin = st.session_state.get("username") == "admin"

if is_admin:
    from ui.tab_gecmis import render as render_gecmis
    from ui.tab_istatistik import render as render_istatistik
    from ui.tab_yonetim_paneli import render as render_yonetim

    tabs = st.tabs(["📋 Denetim Geçmişi", "📊 Denetim İstatistikleri", "⚙️ Yönetim Paneli"])
    with tabs[0]:
        render_gecmis()
    with tabs[1]:
        render_istatistik()
    with tabs[2]:
        render_yonetim()
else:
    from ui.tab_metin_denetimi import render as render_metin
    from ui.tab_gorsel_denetim import render as render_gorsel
    from ui.tab_hukuk_strateji import render as render_hukuk

    tabs = st.tabs(["📝 Metin Denetimi", "🖼️ Görsel Denetim", "⚖️ Hukuk & Strateji Denetimi"])
    with tabs[0]:
        render_metin(selected_model, MODELS)
    with tabs[1]:
        render_gorsel(selected_model, MODELS, _NON_VISION_MODELS)
    with tabs[2]:
        render_hukuk(selected_model)
