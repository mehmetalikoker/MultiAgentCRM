# -*- coding: utf-8 -*-
import logging
import traceback
import streamlit as st

logger = logging.getLogger("agentcrm")


def handle_error(e: Exception, context: str = "") -> None:
    """
    Exception'ı sunucuda loglar, kullanıcıya yalnızca genel bir mesaj gösterir.
    context: hangi işlem sırasında hata oluştuğunu belirtir (log'a eklenir).
    """
    detail = traceback.format_exc()
    log_msg = f"[{context}] {type(e).__name__}: {e}\n{detail}" if context else detail
    logger.error(log_msg)
    st.error("Bir hata oluştu. Lütfen tekrar deneyin veya yöneticinizle iletişime geçin.")
