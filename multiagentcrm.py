# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
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

from streamlit_cookies_controller import CookieController
from user.db import load_users, update_password, get_user_by_email, set_active_token, get_active_token, clear_active_token
from user.jwt_auth import create_jwt, verify_jwt
from user.rate_limiter import record_failure, record_success, attempts_remaining
from user.reset_tokens import create_token, verify_token, consume_token
from user.mailer import send_reset_email

_cookie = CookieController()


def _check_credentials(username: str, password: str) -> bool:
    users = load_users()
    user = users.get(username)
    if not user:
        return False
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return hashed == user["password_hash"]


def _load_asset(path: str) -> str:
    _base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_base, path), encoding="utf-8") as f:
        return f.read()

def _bank_hero() -> str:
    svg = _load_asset("ui/assets/bank_hero.svg")
    return f'<div style="text-align:center; margin-bottom:-4px; padding-top:28px;">{svg}</div>'


def _show_login():
    if st.session_state.pop("kicked_out", False):
        st.warning("Hesabınıza başka bir cihazdan giriş yapıldığı için oturumunuz sonlandırıldı.")

    st.markdown("""<style>
html, body, [data-testid="stAppViewContainer"] {
    background-color: #eef2f7 !important;
    background-image:
        radial-gradient(ellipse at 25%% 80%%, rgba(255,98,0,0.06) 0%%, transparent 50%%),
        radial-gradient(ellipse at 75%% 20%%, rgba(180,210,240,0.35) 0%%, transparent 50%%),
        linear-gradient(160deg, #dce8f5 0%%, #eef2f7 55%%, #dce8f5 100%%) !important;
    background-attachment: fixed !important;
}
[data-testid="stSidebar"] { display: none !important; }
.ing-login-card { margin-top: 0 !important; }
</style>""", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 1.1, 1])
    with col_center:
        step = st.session_state.get("reset_step", "login")

        # ── Adım 1: E-posta ile kod iste ─────────────────────────────────────
        if step == "request":
            st.markdown("""
            <div class="ing-login-card">
                <div class="ing-login-title"><span style="color:#FF6200;">Şifre Sıfırlama</span></div>
                <div class="ing-login-sub">Kayıtlı e-posta adresinize sıfırlama kodu gönderilecek</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='background:#fff; border-radius:0 0 12px 12px; padding:0 36px 32px; "
                        "box-shadow:0 4px 24px rgba(0,0,0,0.10); margin-top:-8px;'>",
                        unsafe_allow_html=True)
            with st.form("reset_request_form"):
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                email_input = st.text_input("E-posta Adresi", placeholder="ornek@sirket.com")
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                col_send, col_back = st.columns(2)
                with col_send:
                    send_btn = st.form_submit_button("Kod Gönder", use_container_width=True, type="primary")
                with col_back:
                    back_btn = st.form_submit_button("Geri Dön", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            if back_btn:
                st.session_state.pop("reset_step", None)
                st.rerun()
            if send_btn:
                user_record = get_user_by_email(email_input)
                if user_record:
                    try:
                        code = create_token(user_record["username"])
                        send_reset_email(
                            user_record["email"],
                            user_record.get("display_name", user_record["username"]),
                            code,
                        )
                        st.session_state["reset_username"] = user_record["username"]
                        st.session_state["reset_step"] = "verify"
                        st.rerun()
                    except Exception as e:
                        st.error(f"E-posta gönderilemedi: {e}")
                else:
                    # Kullanıcı bulunamasa da aynı mesajı göster (enumeration önlemi)
                    st.session_state["reset_step"] = "verify"
                    st.session_state["reset_username"] = ""
                    st.rerun()

        # ── Adım 2: Kodu doğrula ve yeni şifre belirle ───────────────────────
        elif step == "verify":
            st.markdown("""
            <div class="ing-login-card">
                <div class="ing-login-title"><span style="color:#FF6200;">Kod Doğrulama</span></div>
                <div class="ing-login-sub">E-postanıza gelen 6 haneli kodu girin</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='background:#fff; border-radius:0 0 12px 12px; padding:0 36px 32px; "
                        "box-shadow:0 4px 24px rgba(0,0,0,0.10); margin-top:-8px;'>",
                        unsafe_allow_html=True)
            with st.form("reset_verify_form"):
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                code_input = st.text_input("Doğrulama Kodu", placeholder="123456", max_chars=6)
                new_pass = st.text_input("Yeni Şifre", type="password", placeholder="••••••••")
                new_pass2 = st.text_input("Yeni Şifre (Tekrar)", type="password", placeholder="••••••••")
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                col_confirm, col_back = st.columns(2)
                with col_confirm:
                    confirm_btn = st.form_submit_button("Şifreyi Güncelle", use_container_width=True, type="primary")
                with col_back:
                    back_btn = st.form_submit_button("Geri Dön", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            if back_btn:
                st.session_state.pop("reset_step", None)
                st.session_state.pop("reset_username", None)
                st.rerun()
            if confirm_btn:
                reset_user = st.session_state.get("reset_username", "")
                if not reset_user or not verify_token(reset_user, code_input):
                    st.error("Kod hatalı veya süresi dolmuş.")
                elif new_pass != new_pass2:
                    st.error("Şifreler eşleşmiyor.")
                elif len(new_pass) < 6:
                    st.warning("Şifre en az 6 karakter olmalıdır.")
                else:
                    consume_token(reset_user)
                    update_password(reset_user, new_pass)
                    st.session_state.pop("reset_step", None)
                    st.session_state.pop("reset_username", None)
                    st.success("Şifreniz güncellendi. Giriş yapabilirsiniz.")
                    st.rerun()

        # ── Adım 0: Normal giriş formu ────────────────────────────────────────
        else:
            st.markdown(_bank_hero(), unsafe_allow_html=True)
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
            forgot = st.button("Şifremi Unuttum →", use_container_width=False, type="secondary")
            st.markdown("</div>", unsafe_allow_html=True)

            if forgot:
                st.session_state["reset_step"] = "request"
                st.rerun()

            if submitted:
                users = load_users()
                user_record = users.get(username)
                if user_record and user_record.get("locked"):
                    st.error("Hesabınız kilitlenmiştir. Lütfen yönetici ile iletişime geçin.")
                elif _check_credentials(username, password):
                    record_success(username)
                    display = user_record.get("display_name", username)
                    role = user_record.get("role", "user")
                    jwt_token, token_id = create_jwt(username, display, role)
                    set_active_token(username, token_id)
                    _cookie.set("crm_auth", jwt_token, max_age=8 * 3600)
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["display_name"] = display
                    st.session_state["role"] = role
                    st.session_state["token_id"] = token_id
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


# ─── JWT COOKIE RESTORE ───────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    _jwt_token = _cookie.get("crm_auth")
    if _jwt_token:
        _payload = verify_jwt(_jwt_token)
        _valid = (
            _payload is not None
            and get_active_token(_payload["sub"]) == _payload.get("tid")
        )
        if _valid:
            st.session_state["authenticated"] = True
            st.session_state["username"] = _payload["sub"]
            st.session_state["display_name"] = _payload["display_name"]
            st.session_state["role"] = _payload.get("role", "user")
            st.session_state["token_id"] = _payload["tid"]
            st.rerun()
        else:
            _cookie.remove("crm_auth")  # süresi dolmuş / başka cihazdan login edilmiş

if not st.session_state.get("authenticated"):
    _show_login()
    st.stop()

# ─── AKTİF OTURUM KONTROLÜ (30 sn'de bir) ───────────────────────────────────
_now = time.time()
if _now - st.session_state.get("_token_check_ts", 0) > 30:
    st.session_state["_token_check_ts"] = _now
    _stored_tid = get_active_token(st.session_state.get("username", ""))
    if _stored_tid != st.session_state.get("token_id"):
        _cookie.remove("crm_auth")
        st.session_state.clear()
        st.session_state["kicked_out"] = True
        st.rerun()

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


@st.dialog("📚 Mevzuat Rehberi", width="large")
def _mevzuat_dialog():
    from user.prompt_store import get_prompt

    def _render_content(content: str, search: str):
        current_section = None
        matched_any = False
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("==") and line.endswith("=="):
                current_section = line.strip("= ").strip()
                continue
            if search and search.lower() not in line.lower():
                continue
            if current_section:
                st.markdown(
                    f"<div style='background:#FF6200;color:#fff;padding:6px 12px;"
                    f"border-radius:6px;font-weight:700;font-size:0.82rem;"
                    f"margin:14px 0 6px;'>{current_section}</div>",
                    unsafe_allow_html=True,
                )
                current_section = None
            st.markdown(
                f"<div style='background:#f8f9fb;border-left:3px solid #ddd;"
                f"padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:4px;"
                f"font-size:0.88rem;line-height:1.5;'>{line}</div>",
                unsafe_allow_html=True,
            )
            matched_any = True
        if search and not matched_any:
            st.info("Arama sonucu bulunamadı.")

    tab_uyum, tab_hukuk = st.tabs(["⚖️ Uyum Mevzuatı", "📜 Hukuki Düzenlemeler"])

    with tab_uyum:
        search_u = st.text_input("Ara...", placeholder="Madde veya anahtar kelime", key="srch_uyum")
        content_u = get_prompt("regulations_compliance", "data/regulations_compliance.txt")
        _render_content(content_u, search_u)

    with tab_hukuk:
        search_h = st.text_input("Ara...", placeholder="Madde veya anahtar kelime", key="srch_hukuk")
        content_h = get_prompt("regulations_legal", "data/regulations_legal.txt")
        _render_content(content_h, search_h)


with st.sidebar:
    st.markdown("---")
    display_name = st.session_state.get("display_name", st.session_state.get("username", ""))
    st.markdown(f"<span style='font-size:0.85rem;color:#ccc;'>👤 {display_name} olarak giriş yapıldı</span>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("Çıkış Yap", use_container_width=True, type="secondary"):
        clear_active_token(st.session_state.get("username", ""))
        _cookie.remove("crm_auth")
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
    st.markdown("**📚 Mevzuat Rehberi**")
    st.caption("Kampanya uyum kurallarını ve yasal düzenlemeleri inceleyin.")
    if st.button("Mevzuatı Görüntüle", use_container_width=True):
        _mevzuat_dialog()

    st.markdown("---")
is_admin = st.session_state.get("role") == "admin"

if is_admin:
    st.markdown(
        "<h1 style='color:#FF6200; font-size:2.4rem; border-bottom: 3px solid #FF6200; "
        "padding-bottom:10px; display:block;'>Agentic CRM "
        "<span style='font-size:1.2rem; color:#888; font-weight:400;'>Yönetim Paneli</span></h1>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<h1 style='color:#FF6200; font-size:2.4rem; border-bottom: 3px solid #FF6200; "
        "padding-bottom:10px; display:block;'>Agentic CRM</h1>",
        unsafe_allow_html=True
    )
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

if is_admin:
    from ui.tab_gecmis import render as render_gecmis
    from ui.tab_istatistik import render as render_istatistik
    from ui.tab_yonetim_paneli import render as render_yonetim
    from ui.tab_prompt_yonetimi import render as render_prompt
    from ui.tab_sistem_durumu import render as render_sistem

    tabs = st.tabs(["🖥️ Sistem Durumu", "👥 Kullanıcı Yönetimi", "📝 Mevzuat & Promptlar", "📋 Arama Geçmişi", "📊 Arama İstatistikleri"])

    with tabs[0]:
        render_sistem()
    with tabs[1]:
        render_yonetim()
    with tabs[2]:
        render_prompt()
    with tabs[3]:
        render_gecmis()
    with tabs[4]:
        render_istatistik()
else:
    from ui.tab_metin_denetimi import render as render_metin
    from ui.tab_gorsel_denetim import render as render_gorsel
    from ui.tab_hukuk_strateji import render as render_hukuk
    from ui.tab_karsilastirma import render as render_karsilastirma
    from ui.tab_gecmisim import render as render_gecmisim
    from ui.tab_kampanya_gorseli import render as render_kampanya_gorseli

    main_tabs = st.tabs(["🎨 Kampanya Görseli Oluşturma", "🔍 Kampanya Denetimleri", "📊 Analiz ve Log"])

    with main_tabs[0]:
        render_kampanya_gorseli(selected_model, MODELS, _NON_VISION_MODELS)

    with main_tabs[1]:
        denetim_tabs = st.tabs(["📝 Metin Denetimi", "🖼️ Görsel Denetim", "⚖️ Hukuk & Strateji Denetimi"])
        with denetim_tabs[0]:
            render_metin(selected_model, MODELS)
        with denetim_tabs[1]:
            render_gorsel(selected_model, MODELS, _NON_VISION_MODELS)
        with denetim_tabs[2]:
            render_hukuk(selected_model)

    with main_tabs[2]:
        analiz_tabs = st.tabs(["🔀 Karşılaştırmalı Analiz", "🕓 Denetim Geçmişim"])
        with analiz_tabs[0]:
            render_karsilastirma(selected_model, MODELS)
        with analiz_tabs[1]:
            render_gecmisim()
