from flask import Blueprint, request, jsonify
from datetime import datetime

from ..services.appointments_service import AppointmentsService

bp = Blueprint("appointments", __name__)


def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value)


@bp.get("/")
def list_appointments():
    status = request.args.get("status")
    user_id = request.args.get("user_id")

    appts = AppointmentsService.list_appointments(
        status=status,
        user_id=user_id
    )

    return jsonify([a.to_dict() for a in appts]), 200


@bp.post("/")
def request_appointment():
    payload = request.get_json(force=True)

    if "user_id" not in payload or not payload["user_id"]:
        return jsonify({"error": "user_id is required"}), 400

    if not payload.get("description"):
        return jsonify({"error": "description is required"}), 400

    payload["requested_start"] = parse_dt(payload.get("requested_start"))
    payload["requested_end"] = parse_dt(payload.get("requested_end"))

    appt = AppointmentsService.request_appointment(payload)
    return jsonify(appt.to_dict()), 201


@bp.post("/<uuid:appointment_id>/confirm")
def confirm_appointment(appointment_id):
    payload = request.get_json(force=True)

    scheduled_start = parse_dt(payload.get("scheduled_start"))
    scheduled_end = parse_dt(payload.get("scheduled_end"))

    if not scheduled_start or not scheduled_end:
        return jsonify({"error": "scheduled_start and scheduled_end are required"}), 400

    appt = AppointmentsService.admin_confirm(
        appointment_id,
        scheduled_start,
        scheduled_end
    )

    return jsonify(appt.to_dict()), 200


@bp.post("/<uuid:appointment_id>/mark-paid")
def mark_paid(appointment_id):
    appt = AppointmentsService.mark_paid(appointment_id)
    return jsonify(appt.to_dict()), 200
