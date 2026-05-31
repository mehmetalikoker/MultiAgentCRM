# -*- coding: utf-8 -*-
import streamlit as st
from user.prompt_store import get_prompt, save_prompt, get_history, get_prompt_meta, rollback_prompt

_PROMPTS = {
    "compliance": {
        "label": "Metin Denetimi Promptu",
        "fallback": "prompts/compliance.txt",
        "description": "Kampanya metni denetiminde LLM'e gönderilen şablon. "
                       "`{context}`, `{campaign_text}`, `{channel}` yer tutucularını koruyun.",
        "type": "prompt",
    },
    "legal_strategy": {
        "label": "Hukuk & Strateji Promptu",
        "fallback": "prompts/legal_strategy.txt",
        "description": "Hukuki denetimde kullanılan şablon. "
                       "`{legal_context}`, `{campaign_text}` yer tutucularını koruyun.",
        "type": "prompt",
    },
    "visual_control": {
        "label": "Görsel Denetim Promptu",
        "fallback": "prompts/visual_control.txt",
        "description": "Görsel denetimde kullanılan şablon. `{campaign_text}` yer tutucusunu koruyun.",
        "type": "prompt",
    },
    "security_system": {
        "label": "Güvenlik Sistem Promptu",
        "fallback": "prompts/security_system.txt",
        "description": "Tüm denetimlerde sistem mesajı olarak eklenen prompt injection önleme talimatı.",
        "type": "prompt",
    },
    "regulations_compliance": {
        "label": "Mevzuat — Metin Denetimi",
        "fallback": "data/regulations_compliance.txt",
        "description": "Metin denetiminde RAG kaynağı olarak kullanılan mevzuat maddeleri. "
                       "Her satır ayrı bir madde olarak işlenir.",
        "type": "regulation",
    },
    "regulations_legal": {
        "label": "Mevzuat — Hukuk Denetimi",
        "fallback": "data/regulations_legal.txt",
        "description": "Hukuki denetimde yedek RAG kaynağı. Her satır ayrı bir madde olarak işlenir.",
        "type": "regulation",
    },
}


def render():
    st.header("Mevzuat & Prompt Yönetimi")
    st.markdown("Denetim ajanlarının kullandığı prompt şablonlarını ve mevzuat metinlerini düzenleyin.")

    col_sel, col_edit = st.columns([1, 2.5])

    with col_sel:
        st.subheader("Düzenlenecek İçerik")

        prompt_options = list(_PROMPTS.keys())
        selected_key = st.radio(
            "İçerik Seçin",
            options=prompt_options,
            format_func=lambda k: _PROMPTS[k]["label"],
            label_visibility="collapsed",
        )

        meta = get_prompt_meta(selected_key)
        if meta:
            st.markdown("---")
            st.caption(
                f"Son güncelleme:\n\n"
                f"**{meta.get('updated_by', '—')}** tarafından\n\n"
                f"`{meta.get('updated_at', '—')}`"
            )
        else:
            st.markdown("---")
            st.caption("Henüz düzenlenmedi — dosyadan okunuyor.")

    with col_edit:
        cfg = _PROMPTS[selected_key]

        st.subheader(cfg["label"])

        type_badge = "📄 Prompt Şablonu" if cfg["type"] == "prompt" else "📋 Mevzuat Metni"
        st.markdown(f"`{type_badge}`")
        st.info(cfg["description"])

        current_content = get_prompt(selected_key, cfg["fallback"])

        edited = st.text_area(
            "İçerik",
            value=current_content,
            height=420,
            label_visibility="collapsed",
            key=f"editor_{selected_key}",
        )

        col_save, col_reset = st.columns([1, 1])

        with col_save:
            if st.button("💾 Kaydet", type="primary", use_container_width=True):
                if not edited.strip():
                    st.error("İçerik boş bırakılamaz.")
                elif edited.strip() == current_content.strip():
                    st.warning("Değişiklik yapılmadı.")
                else:
                    save_prompt(
                        selected_key,
                        edited.strip(),
                        st.session_state.get("username", "admin"),
                    )
                    st.success("Kaydedildi. Değişiklikler bir sonraki denetimde geçerli olacak.")
                    st.rerun()

        with col_reset:
            if st.button("↩ Dosyadan Yükle", use_container_width=True):
                st.session_state[f"reset_confirm_{selected_key}"] = True

        if st.session_state.pop(f"reset_confirm_{selected_key}", False):
            from pathlib import Path
            file_content = (Path(__file__).parent.parent / cfg["fallback"]).read_text(encoding="utf-8")
            save_prompt(
                selected_key,
                file_content.strip(),
                st.session_state.get("username", "admin"),
            )
            st.success("Orijinal dosya içeriği yüklendi ve kaydedildi.")
            st.rerun()

    # ── Versiyon Geçmişi ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🕓 Versiyon Geçmişi", expanded=False):
        history = get_history(selected_key)

        if not history:
            st.info("Henüz geçmiş versiyon yok.")
        else:
            st.caption(f"Son {len(history)} versiyon gösteriliyor.")
            for i, ver in enumerate(history):
                col_info, col_prev, col_roll = st.columns([2, 3, 1])
                with col_info:
                    st.markdown(
                        f"**v{i + 1}** &nbsp; `{ver.get('updated_at', '—')}`  \n"
                        f"_{ver.get('updated_by', '—')}_"
                    )
                with col_prev:
                    preview = ver["content"][:120].replace("\n", " ")
                    st.caption(f"{preview}{'…' if len(ver['content']) > 120 else ''}")
                with col_roll:
                    if st.button("Geri Al", key=f"rollback_{selected_key}_{i}",
                                 use_container_width=True):
                        rollback_prompt(
                            selected_key, i,
                            st.session_state.get("username", "admin"),
                        )
                        st.success(f"v{i + 1} geri yüklendi.")
                        st.rerun()
                st.markdown("<hr style='margin:6px 0; opacity:0.15;'>", unsafe_allow_html=True)
