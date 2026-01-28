# app/services/email_service.py
import os
import smtplib
import socket
from email.message import EmailMessage
from typing import Optional

DEFAULT_TIMEOUT_SECONDS = int(os.getenv("SMTP_TIMEOUT", "10"))


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """
    Envía un correo. Devuelve True si se envió, False si falló.
    IMPORTANTE: No levanta exception para no tumbar requests.
    """

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    from_name = os.getenv("EMAIL_FROM_NAME", "Fisioterapia RH")

    # TLS (587) vs SSL (465)
    use_ssl = os.getenv("SMTP_SSL", "").lower() in ("1", "true", "yes") or port == 465

    if not host or not user or not pwd:
        # En prod preferible log, pero devolvemos False sin reventar
        print("[MAIL] SMTP no configurado (SMTP_HOST/SMTP_USER/SMTP_PASS).")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to_email

    if text_body:
        msg.set_content(text_body)
    else:
        msg.set_content("Este correo requiere un cliente que soporte HTML.")

    msg.add_alternative(html_body, subtype="html")

    try:
        if use_ssl:
            # SMTP SSL (normalmente 465)
            with smtplib.SMTP_SSL(host, port, timeout=DEFAULT_TIMEOUT_SECONDS) as server:
                server.ehlo()
                server.login(user, pwd)
                server.send_message(msg)
        else:
            # SMTP STARTTLS (normalmente 587)
            with smtplib.SMTP(host, port, timeout=DEFAULT_TIMEOUT_SECONDS) as server:
                server.ehlo()
                # Para STARTTLS seguro
                server.starttls()
                server.ehlo()
                server.login(user, pwd)
                server.send_message(msg)

        return True

    except (smtplib.SMTPException, socket.timeout, OSError) as e:
        return False
