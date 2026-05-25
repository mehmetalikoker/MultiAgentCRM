# -*- coding: utf-8 -*-
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
load_dotenv()

_SMTP_HOST = os.getenv("SMTP_HOST", "")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER = os.getenv("SMTP_USER", "")
_SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
_SMTP_FROM = os.getenv("SMTP_FROM", _SMTP_USER)


def send_reset_email(to_email: str, display_name: str, code: str) -> None:
    """Şifre sıfırlama kodunu e-posta olarak gönderir."""
    if not all([_SMTP_HOST, _SMTP_USER, _SMTP_PASSWORD]):
        raise RuntimeError(
            "SMTP ayarları eksik. .env dosyasına SMTP_HOST, SMTP_USER, "
            "SMTP_PASSWORD değerlerini ekleyin."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Agentic CRM — Şifre Sıfırlama Kodu"
    msg["From"] = _SMTP_FROM
    msg["To"] = to_email

    plain = (
        f"Merhaba {display_name},\n\n"
        f"Şifre sıfırlama kodunuz: {code}\n\n"
        "Bu kod 30 dakika geçerlidir.\n\n"
        "Bu isteği siz yapmadıysanız bu e-postayı dikkate almayınız.\n\n"
        "— Agentic CRM"
    )

    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:480px;margin:0 auto;">
      <div style="border-top:5px solid #FF6200;border-radius:8px 8px 0 0;background:#fff;
                  padding:32px 36px 8px;">
        <div style="font-size:1.8rem;font-weight:900;color:#FF6200;margin-bottom:4px;">
          Agentic CRM
        </div>
        <h2 style="color:#333;font-size:1.1rem;margin-top:0;">Şifre Sıfırlama</h2>
      </div>
      <div style="background:#fff;padding:8px 36px 32px;border-radius:0 0 8px 8px;
                  box-shadow:0 4px 16px rgba(0,0,0,0.08);">
        <p style="color:#555;">Merhaba <strong>{display_name}</strong>,</p>
        <p style="color:#555;">Şifre sıfırlama talebiniz alındı. Aşağıdaki kodu giriş
           ekranına giriniz:</p>
        <div style="text-align:center;margin:28px 0;">
          <span style="font-size:2.4rem;font-weight:900;letter-spacing:10px;
                       color:#FF6200;background:#fff1ea;padding:14px 28px;
                       border-radius:8px;">{code}</span>
        </div>
        <p style="color:#888;font-size:0.85rem;">
          Bu kod <strong>30 dakika</strong> geçerlidir.<br>
          Bu isteği siz yapmadıysanız bu e-postayı dikkate almayınız.
        </p>
      </div>
    </div>
    """

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
        server.starttls()
        server.login(_SMTP_USER, _SMTP_PASSWORD)
        server.sendmail(_SMTP_FROM, to_email, msg.as_string())
