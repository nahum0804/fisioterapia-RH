import os
from zoneinfo import ZoneInfo
from datetime import datetime

from app.services.email_service import send_email

CR_TZ = ZoneInfo("America/Costa_Rica")

def _fmt(dt: datetime | None) -> str:
    if not dt:
        return "Pendiente"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(CR_TZ).strftime("%d/%m/%Y %I:%M %p")

def _status_es(status: str) -> str:
    return {
        "requested": "Solicitada",
        "confirmed": "Confirmada",
        "cancelled": "Cancelada",
    }.get(status, status)

def _admin_email() -> str:
    email = os.getenv("ADMIN_EMAIL")
    if not email:
        raise RuntimeError("Falta ADMIN_EMAIL en variables de entorno.")
    return email


def email_on_request(user_email: str, user_name: str, appt) -> None:
    status = _status_es(appt.status)

    subject_user = f"Solicitud de cita recibida ({status})"
    html_user = f"""
    <h2>Hola {user_name},</h2>
    <p>Recibimos tu solicitud de cita.</p>
    <ul>
      <li><b>Estado:</b> {status}</li>
      <li><b>Rango solicitado:</b> {_fmt(appt.requested_start)} - {_fmt(appt.requested_end)}</li>
    </ul>
    <p>Te notificaremos cuando sea confirmada.</p>
    <p><i>Fisioterapia RH</i></p>
    """
    _safe_send(user_email, subject_user, html_user)

    # Admin
    subject_admin = f"[Admin] Nueva solicitud de cita ({status})"
    html_admin = f"""
    <h2>Nueva solicitud de cita</h2>
    <ul>
      <li><b>Paciente:</b> {user_name} ({user_email})</li>
      <li><b>Estado:</b> {status}</li>
      <li><b>Rango solicitado:</b> {_fmt(appt.requested_start)} - {_fmt(appt.requested_end)}</li>
      <li><b>ID cita:</b> {appt.id}</li>
    </ul>
    """
    _safe_send(_admin_email(), subject_admin, html_admin)


def email_on_confirm(user_email: str, user_name: str, appt) -> None:
    subject = f"Tu cita fue confirmada ({_fmt(appt.scheduled_start)})"
    html = f"""
    <h2>Hola {user_name},</h2>
    <p>Tu cita ha sido <b>confirmada</b>.</p>
    <ul>
      <li><b>Fecha y hora:</b> {_fmt(appt.scheduled_start)} - {_fmt(appt.scheduled_end)}</li>
      <li><b>Estado:</b> {_status_es(appt.status)}</li>
    </ul>
    <p><i>Fisioterapia RH</i></p>
    """
    _safe_send(user_email, subject, html)


def email_on_cancel(user_email: str, user_name: str, appt, reason: str | None = None) -> None:
    subject = "Tu cita fue cancelada"
    html = f"""
    <h2>Hola {user_name},</h2>
    <p>Tu cita fue <b>cancelada</b>.</p>
    <ul>
      <li><b>Estado:</b> {_status_es(appt.status)}</li>
      <li><b>Horario:</b> {_fmt(appt.scheduled_start)} - {_fmt(appt.scheduled_end)}</li>
    </ul>
    {f"<p><b>Motivo:</b> {reason}</p>" if reason else ""}
    <p><i>Fisioterapia RH</i></p>
    """
    _safe_send(user_email, subject, html)


def _safe_send(to_email: str, subject: str, html_body: str) -> None:
    """
    Para que si el SMTP falla, no te rompa el endpoint.
    Ideal: usar logger en vez de print.
    """
    try:
        send_email(to_email=to_email, subject=subject, html_body=html_body)
    except Exception as e:
        print(f"[MAIL] Falló envío a {to_email}: {e}")
