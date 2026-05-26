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

from streamlit_cookies_controller import CookieController
from user.db import load_users, update_password, get_user_by_email
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


_BANK_SVG = """
<div style="text-align:center; margin-bottom:-4px; padding-top:28px;">
<svg width="340" height="112" viewBox="0 0 340 112" xmlns="http://www.w3.org/2000/svg">
  <circle cx="25"  cy="12" r="1.2" fill="rgba(100,140,190,0.40)"/>
  <circle cx="65"  cy="6"  r="0.8" fill="rgba(100,140,190,0.30)"/>
  <circle cx="110" cy="19" r="1.0" fill="rgba(100,140,190,0.35)"/>
  <circle cx="230" cy="9"  r="1.2" fill="rgba(100,140,190,0.40)"/>
  <circle cx="280" cy="14" r="0.8" fill="rgba(100,140,190,0.30)"/>
  <circle cx="316" cy="5"  r="1.0" fill="rgba(100,140,190,0.35)"/>
  <rect x="0"  y="74" width="28" height="38" rx="1" fill="rgba(100,140,200,0.18)"/>
  <rect x="4"  y="80" width="4" height="5" fill="rgba(80,120,180,0.25)"/>
  <rect x="12" y="80" width="4" height="5" fill="rgba(80,120,180,0.25)"/>
  <rect x="20" y="80" width="4" height="5" fill="rgba(80,120,180,0.25)"/>
  <rect x="35" y="58" width="35" height="54" rx="1" fill="rgba(100,140,200,0.20)"/>
  <rect x="39" y="64" width="5" height="7" fill="rgba(80,120,180,0.28)"/>
  <rect x="49" y="64" width="5" height="7" fill="rgba(80,120,180,0.28)"/>
  <rect x="59" y="64" width="5" height="7" fill="rgba(80,120,180,0.28)"/>
  <rect x="39" y="76" width="5" height="7" fill="rgba(80,120,180,0.20)"/>
  <rect x="49" y="76" width="5" height="7" fill="rgba(80,120,180,0.20)"/>
  <rect x="59" y="76" width="5" height="7" fill="rgba(80,120,180,0.20)"/>
  <rect x="78" y="68" width="22" height="44" rx="1" fill="rgba(100,140,200,0.18)"/>
  <line x1="170" y1="5"  x2="170" y2="28" stroke="rgba(80,100,140,0.50)" stroke-width="1.5"/>
  <polygon points="170,5 178,12 170,15 162,12" fill="#FF6200" opacity="0.90"/>
  <polygon points="170,28 216,50 124,50" fill="rgba(255,98,0,0.12)"/>
  <line x1="124" y1="50" x2="216" y2="50" stroke="rgba(255,98,0,0.45)" stroke-width="1.5"/>
  <rect x="122" y="50" width="96" height="8" fill="rgba(100,140,200,0.15)"/>
  <rect x="128" y="58" width="7" height="54" rx="1" fill="rgba(80,120,180,0.22)"/>
  <rect x="142" y="58" width="7" height="54" rx="1" fill="rgba(80,120,180,0.22)"/>
  <rect x="156" y="58" width="7" height="54" rx="1" fill="rgba(80,120,180,0.28)"/>
  <rect x="170" y="58" width="7" height="54" rx="1" fill="rgba(80,120,180,0.28)"/>
  <rect x="184" y="58" width="7" height="54" rx="1" fill="rgba(80,120,180,0.22)"/>
  <rect x="198" y="58" width="7" height="54" rx="1" fill="rgba(80,120,180,0.22)"/>
  <rect x="118" y="110" width="104" height="3" fill="rgba(255,98,0,0.35)"/>
  <rect x="115" y="113" width="110" height="2" fill="rgba(255,98,0,0.18)"/>
  <rect x="240" y="66" width="22" height="46" rx="1" fill="rgba(100,140,200,0.18)"/>
  <rect x="270" y="52" width="35" height="60" rx="1" fill="rgba(100,140,200,0.20)"/>
  <rect x="274" y="58" width="5" height="7" fill="rgba(80,120,180,0.28)"/>
  <rect x="284" y="58" width="5" height="7" fill="rgba(80,120,180,0.28)"/>
  <rect x="294" y="58" width="5" height="7" fill="rgba(80,120,180,0.28)"/>
  <rect x="274" y="70" width="5" height="7" fill="rgba(80,120,180,0.20)"/>
  <rect x="284" y="70" width="5" height="7" fill="rgba(80,120,180,0.20)"/>
  <rect x="294" y="70" width="5" height="7" fill="rgba(80,120,180,0.20)"/>
  <rect x="312" y="76" width="28" height="36" rx="1" fill="rgba(100,140,200,0.18)"/>
  <line x1="0"   y1="40" x2="108" y2="40" stroke="rgba(100,140,200,0.15)" stroke-width="0.5"/>
  <line x1="232" y1="40" x2="340" y2="40" stroke="rgba(100,140,200,0.15)" stroke-width="0.5"/>
  <line x1="0" y1="112" x2="340" y2="112" stroke="rgba(255,98,0,0.35)" stroke-width="1"/>
</svg>
</div>
"""


def _show_login():
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
            st.markdown(_BANK_SVG, unsafe_allow_html=True)
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
                    _cookie.set("crm_auth", create_jwt(username, display), max_age=8 * 3600)
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["display_name"] = display
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
        if _payload:
            st.session_state["authenticated"] = True
            st.session_state["username"] = _payload["sub"]
            st.session_state["display_name"] = _payload["display_name"]
            st.rerun()
        else:
            _cookie.remove("crm_auth")  # süresi dolmuş / geçersiz

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
