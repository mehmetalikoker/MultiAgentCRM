# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import hashlib
import streamlit as st
import tempfile
import json

st.set_page_config(
    page_title="Kampanya Denetim Sistemi",
    page_icon="🏦",
    layout="wide"
)

# ─── ING MARKA TEMASı ─────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Genel ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #f5f5f5;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* ── Primary butonlar ── */
.stButton > button[kind="primary"],
.stFormSubmitButton > button {
    background-color: #FF6200 !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    letter-spacing: 0.3px;
    transition: background-color 0.2s ease;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover {
    background-color: #d95300 !important;
    color: #ffffff !important;
}

/* ── Sekunder (çıkış) butonu ── */
.stButton > button[kind="secondary"] {
    border: 1.5px solid #FF6200 !important;
    color: #FF6200 !important;
    background-color: transparent !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
.stButton > button[kind="secondary"]:hover {
    background-color: #fff1ea !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #1c1c1c !important;
    border-right: 3px solid #FF6200;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #f0f0f0 !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #2e2e2e !important;
    color: #f0f0f0 !important;
    border: 1px solid #FF6200 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #FF6200 !important;
    opacity: 0.4;
}

/* ── Başlık çizgisi ── */
h1 { border-bottom: 3px solid #FF6200; padding-bottom: 8px; display: inline-block; }

/* ── Tab bar ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 2px solid #e0e0e0;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    color: #555 !important;
    padding: 10px 20px;
    border-radius: 6px 6px 0 0;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #FF6200 !important;
    background-color: #fff1ea !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #FF6200 !important;
    height: 3px;
}

/* ── Input odak rengi ── */
input:focus, textarea:focus {
    border-color: #FF6200 !important;
    box-shadow: 0 0 0 2px rgba(255,98,0,0.15) !important;
}

/* ── Login kartı ── */
.ing-login-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 40px 36px 32px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.10);
    border-top: 5px solid #FF6200;
    margin-top: 60px;
}
.ing-logo-text {
    font-size: 2.8rem;
    font-weight: 900;
    color: #FF6200;
    letter-spacing: -1px;
    text-align: center;
    line-height: 1;
}
.ing-login-title {
    font-size: 1.1rem;
    color: #333;
    font-weight: 600;
    text-align: center;
    margin-top: 6px;
    margin-bottom: 4px;
}
.ing-login-sub {
    font-size: 0.85rem;
    color: #888;
    text-align: center;
    margin-bottom: 24px;
}

/* ── Uygunluk puanı renkleri ── */
.score-high { color: #FF6200 !important; }
</style>
""", unsafe_allow_html=True)

# ─── KİMLİK DOĞRULAMA ─────────────────────────────────────────────────────────

_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")


def _load_users() -> dict:
    if not os.path.exists(_USERS_FILE):
        return {}
    with open(_USERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {u["username"]: u for u in data.get("users", [])}


def _check_credentials(username: str, password: str) -> bool:
    users = _load_users()
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
            <div class="ing-login-title">Agentic CRM</div>
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
            if _check_credentials(username, password):
                users = _load_users()
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["display_name"] = users[username].get("display_name", username)
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")


if not st.session_state.get("authenticated"):
    _show_login()
    st.stop()

MODELS = {
    # OpenAI
    "gpt-4o":                    "GPT-4o",
    "gpt-4o-mini":               "GPT-4o Mini",
    "gpt-4-turbo":               "GPT-4 Turbo",
    "gpt-3.5-turbo":             "GPT-3.5 Turbo",
    # Anthropic
    "claude-opus-4-7":           "Claude Opus 4.7",
    "claude-sonnet-4-6":         "Claude Sonnet 4.6",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    # Google Gemini
    # "gemini-2.0-flash":          "Gemini 2.0 Flash",
    # "gemini-1.5-pro":            "Gemini 1.5 Pro",
    # "gemini-1.5-flash":          "Gemini 1.5 Flash",
    
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
    "<h1 style='color:#1c1c1c; font-size:2.4rem; border-bottom: 3px solid #FF6200; "
    "padding-bottom:10px; display:block;'>Agentic CRM</h1>",
    unsafe_allow_html=True
)
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "📝 Metin Denetimi",
    "🖼️ Görsel Denetim",
    "⚖️ Hukuk & Strateji Denetimi"
])

# ─── TAB 1: Kampanya Metin Denetimi ───────────────────────────────────────────
with tab1:
    st.header("Kampanya Metin Denetimi")
    st.markdown("Kampanya metninizi girin ve hangi kanalda yayınlanacağını seçin.")

    col1, col2 = st.columns([3, 1])

    with col1:
        campaign_text = st.text_area(
            "Kampanya Metni",
            placeholder="Kampanya metninizi buraya girin...",
            height=180
        )

    with col2:
        channel = st.selectbox(
            "Kampanya Kanalı",
            options=[
                "SMS",
                "E-posta",
                "Mobil Inbound Kampanya",
                "Şube İçi Inbound Kampanya",
                "Push Bildirimi",
            ]
        )
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Denetle", type="primary", use_container_width=True)

    if run_btn:
        if not campaign_text.strip():
            st.warning("Lütfen kampanya metnini girin.")
        else:
            with st.spinner("Metin denetleniyor..."):
                try:
                    from agents.campaigntextagent import app
                    result = app.invoke({
                        "campaign_text": campaign_text,
                        "channel": channel,
                        "selected_model": selected_model,
                    })

                    is_safe = result.get("is_safe", False)
                    report = result.get("compliance_report", "")

                    st.markdown("---")
                    st.subheader("Denetim Sonucu")

                    if is_safe:
                        st.success("✅ Kampanya metni uygun bulundu.")
                    else:
                        st.error("❌ Kampanya metninde sorunlar tespit edildi.")

                    st.markdown(f"**Kanal:** `{channel}` &nbsp;|&nbsp; **Model:** `{MODELS[selected_model]}`")
                    st.markdown("**Detaylı Rapor:**")
                    try:
                        clean = report.strip()
                        if clean.startswith("```"):
                            parts = clean.split("```")
                            clean = parts[1].lstrip("json").strip() if len(parts) > 1 else clean
                        st.json(json.loads(clean))
                    except (json.JSONDecodeError, ValueError):
                        st.markdown(
                            f"<pre style='white-space: pre-wrap; word-wrap: break-word; "
                            f"background:#f6f8fa; padding:1rem; border-radius:0.5rem; "
                            f"font-size:0.85rem; overflow-x:hidden;'>{report}</pre>",
                            unsafe_allow_html=True
                        )

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

# ─── TAB 2: Görsel Denetim ────────────────────────────────────────────────────
with tab2:
    st.header("Görsel Denetim")
    st.markdown("Denetlenecek kampanya görselini ve onaylanmış metni girin.")

    _vision_models = [name for key, name in MODELS.items() if key not in _NON_VISION_MODELS]
    _non_vision_names = [MODELS[k] for k in _NON_VISION_MODELS if k in MODELS]

    if selected_model in _NON_VISION_MODELS:
        st.error(
            f"**{MODELS[selected_model]}** görüntü işlemeyi desteklemiyor. "
            f"Sol menüden görsel destekli bir model seçin."
        )
        st.info(
            "**Görsel denetim destekleyen modeller:** "
            + " · ".join(_vision_models)
        )
    else:
        st.info(
            f"**Aktif model:** {MODELS[selected_model]} &nbsp;·&nbsp; Görsel denetim destekleniyor.  \n"
            f"Desteklenmeyen modeller: {', '.join(_non_vision_names)}",
            icon="ℹ️",
        )

    uploaded_file = st.file_uploader(
        "Kampanya Görseli", type=["jpg", "jpeg", "png"]
    )

    approved_text = st.text_area(
        "Onaylanmış Kampanya Metni",
        placeholder="Daha önce onaylanan kampanya metnini buraya girin...",
        height=120
    )

    if st.button("Görseli Denetle", type="primary"):
        if not uploaded_file:
            st.warning("Lütfen bir görsel yükleyin.")
        elif not approved_text.strip():
            st.warning("Lütfen onaylanmış kampanya metnini girin.")
        else:
            with st.spinner("Görsel denetleniyor..."):
                try:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
                    ) as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    from agents.visualcontrolagent import app as visual_app
                    result = visual_app.invoke({
                        "campaign_text": approved_text,
                        "image_path": tmp_path,
                        "selected_model": selected_model,
                    })
                    os.unlink(tmp_path)

                    is_visual_safe = result.get("is_visual_safe", False)
                    report = result.get("visual_report", "")

                    st.markdown("---")
                    st.subheader("Görsel Denetim Sonucu")
                    col_img, col_report = st.columns([1, 2])
                    with col_img:
                        st.image(uploaded_file, caption="Yüklenen Görsel", use_container_width=True)
                    with col_report:
                        if is_visual_safe:
                            st.success("✅ Görsel uygun bulundu.")
                        else:
                            st.error("❌ Görselde sorunlar tespit edildi.")
                        st.markdown("**Detaylı Rapor:**")
                        st.markdown(report)

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

# ─── TAB 3: Hukuk & Strateji Denetimi ────────────────────────────────────────
with tab3:
    st.header("Hukuk & Strateji Denetimi")
    st.markdown("Hukuki belgeleri yükleyin, kampanya metni bu belgelere göre denetlenecektir.")

    # Dosya yükleme
    uploaded_docs = st.file_uploader(
        "Hukuki Belgeler (PDF veya TXT — birden fazla dosya seçebilirsiniz)",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )

    if uploaded_docs:
        st.success(f"✅ {len(uploaded_docs)} belge yüklendi: {', '.join(f.name for f in uploaded_docs)}")

    st.markdown("")
    legal_campaign_text = st.text_area(
        "Kampanya Metni",
        placeholder="Hukuki açıdan denetlenecek kampanya metnini girin...",
        height=140
    )

    if st.button("Hukuki Denetim Yap", type="primary"):
        if not legal_campaign_text.strip():
            st.warning("Lütfen kampanya metnini girin.")
        else:
            with st.spinner("Belgeler işleniyor ve hukuki denetim yapılıyor..."):
                try:
                    # Yüklenen dosyalardan metin çıkar
                    legal_chunks: list[str] = []

                    if uploaded_docs:
                        from langchain_community.document_loaders import PyPDFLoader, TextLoader
                        from langchain.text_splitter import RecursiveCharacterTextSplitter

                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=800, chunk_overlap=100
                        )

                        for doc_file in uploaded_docs:
                            suffix = os.path.splitext(doc_file.name)[1].lower()
                            with tempfile.NamedTemporaryFile(
                                delete=False, suffix=suffix
                            ) as tmp:
                                tmp.write(doc_file.read())
                                tmp_path = tmp.name

                            if suffix == ".pdf":
                                loader = PyPDFLoader(tmp_path)
                            else:
                                loader = TextLoader(tmp_path, encoding="utf-8")

                            pages = loader.load()
                            chunks = splitter.split_documents(pages)
                            legal_chunks.extend([c.page_content for c in chunks])
                            os.unlink(tmp_path)

                    from agents.legalstrategyagent import app as legal_app
                    result = legal_app.invoke({
                        "campaign_text": legal_campaign_text,
                        "legal_documents": legal_chunks,
                        "selected_model": selected_model,
                    })

                    report = result.get("legal_audit_report", "")
                    score = result.get("final_score", 0)

                    st.markdown("---")
                    st.subheader("Hukuki Denetim Sonucu")

                    col_score, col_report = st.columns([1, 3])
                    with col_score:
                        color = "green" if score >= 70 else "orange" if score >= 40 else "red"
                        st.markdown(
                            f"<h1 style='color:{color}; text-align:center'>{score}/100</h1>"
                            f"<p style='text-align:center'>Uygunluk Puanı</p>",
                            unsafe_allow_html=True
                        )
                    with col_report:
                        if uploaded_docs:
                            st.caption(f"Kaynak belgeler: {', '.join(f.name for f in uploaded_docs)}")
                        else:
                            st.caption("Belge yüklenmedi — varsayılan BDDK mevzuatı kullanıldı.")
                        st.markdown(report)

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
