from flask import Blueprint, request, jsonify
from datetime import datetime
from ..services.appointments_service import AppointmentsService

bp = Blueprint("appointments", __name__)

def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

@bp.get("/")
def list_appointments():
    status = request.args.get("status")
    user_id = request.args.get("user_id")
    appts = AppointmentsService.list_appointments(status=status, user_id=user_id)
    return jsonify([a.to_dict() for a in appts]), 200

@bp.post("/")
def request_appointment():
    payload = request.get_json(force=True)

    # user_id puede venir (cliente logueado), pero tu caso manual va por otra ruta
    if not payload.get("description"):
        return jsonify({"error": "description is required"}), 400

    payload["requested_start"] = parse_dt(payload.get("requested_start"))
    appt = AppointmentsService.request_appointment(payload)
    return jsonify(appt.to_dict()), 201

@bp.post("/<uuid:appointment_id>/confirm")
def confirm_appointment(appointment_id):
    payload = request.get_json(force=True)
    scheduled_start = parse_dt(payload.get("scheduled_start"))
    if not scheduled_start:
        return jsonify({"error": "scheduled_start is required"}), 400

    appt = AppointmentsService.admin_confirm(appointment_id, scheduled_start)
    return jsonify(appt.to_dict()), 200

# ---- Manual CRUD (doctor) ----
@bp.post("/manual")
def create_manual():
    payload = request.get_json(force=True)
    payload["scheduled_start"] = parse_dt(payload.get("scheduled_start"))
    if not payload["scheduled_start"]:
        return jsonify({"error": "scheduled_start is required"}), 400
    appt = AppointmentsService.create_manual(payload)
    return jsonify(appt.to_dict()), 201

@bp.put("/<uuid:appointment_id>")
def update_appointment(appointment_id):
    payload = request.get_json(force=True)
    if "scheduled_start" in payload:
        payload["scheduled_start"] = parse_dt(payload.get("scheduled_start"))
    appt = AppointmentsService.update_manual(appointment_id, payload)
    return jsonify(appt.to_dict()), 200

@bp.delete("/<uuid:appointment_id>")
def delete_appointment(appointment_id):
    AppointmentsService.delete_appointment(appointment_id)
    return jsonify({"ok": True}), 200
