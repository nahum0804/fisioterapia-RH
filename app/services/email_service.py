import os
import smtplib
from email.message import EmailMessage

def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")
    from_name = os.getenv("EMAIL_FROM_NAME", "Fisioterapia RH")

    if not host or not user or not pwd:
        raise RuntimeError("SMTP no configurado (SMTP_HOST/SMTP_USER/SMTP_PASS).")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to_email

    if text_body:
        msg.set_content(text_body)
    else:
        msg.set_content("Este correo requiere un cliente que soporte HTML.")

    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, pwd)
        server.send_message(msg)
