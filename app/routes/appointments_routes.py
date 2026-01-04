from flask import Blueprint, request, jsonify, g
from datetime import datetime

from ..services.appointments_service import AppointmentsService
from ..models import Appointment
from ..utils.auth_required import auth_required, admin_required

bp = Blueprint("appointments", __name__)


def parse_dt(value: str | None):
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


@bp.get("/")
@auth_required
def list_appointments():
    status = request.args.get("status")
    user_id = request.args.get("user_id")

    if g.role != "admin":
        user_id = g.user_id  

    appts = AppointmentsService.list_appointments(status=status, user_id=user_id)
    return jsonify([a.to_dict() for a in appts]), 200


@bp.post("/")
@auth_required
def request_appointment():
    payload = request.get_json(force=True) or {}

    payload["user_id"] = g.user_id

    if not payload.get("description"):
        return jsonify({"error": "description is required"}), 400

    payload["requested_start"] = parse_dt(payload.get("requested_start"))
    payload["requested_end"] = parse_dt(payload.get("requested_end"))

    appt = AppointmentsService.request_appointment(payload)
    return jsonify(appt.to_dict()), 201


@bp.post("/<uuid:appointment_id>/confirm")
@auth_required
@admin_required
def confirm_appointment(appointment_id):
    payload = request.get_json(force=True) or {}

    scheduled_start = parse_dt(payload.get("scheduled_start"))
    scheduled_end = parse_dt(payload.get("scheduled_end"))

    if not scheduled_start or not scheduled_end:
        return jsonify({"error": "scheduled_start and scheduled_end are required"}), 400

    appt = AppointmentsService.admin_confirm(appointment_id, scheduled_start, scheduled_end)
    return jsonify(appt.to_dict()), 200


@bp.post("/<uuid:appointment_id>/mark-paid")
@auth_required
@admin_required
def mark_paid(appointment_id):
    appt = AppointmentsService.mark_paid(appointment_id)
    return jsonify(appt.to_dict()), 200


@bp.patch("/<uuid:appointment_id>")
@auth_required
@admin_required
def admin_update_appointment(appointment_id):
    payload = request.get_json(force=True) or {}

    for k in ["requested_start", "requested_end", "scheduled_start", "scheduled_end"]:
        if k in payload:
            payload[k] = parse_dt(payload.get(k))

    appt = AppointmentsService.admin_update(appointment_id, payload)
    return jsonify(appt.to_dict()), 200


@bp.delete("/<uuid:appointment_id>")
@auth_required
def delete_appointment(appointment_id):
    if g.role == "admin":
        AppointmentsService.delete_appointment(appointment_id)
        return jsonify({"ok": True}), 200

    appt = Appointment.query.get_or_404(appointment_id)
    if str(appt.user_id) != str(g.user_id):
        return jsonify({"error": "No autorizado para borrar esta cita"}), 403

    AppointmentsService.delete_appointment(appointment_id)
    return jsonify({"ok": True}), 200
