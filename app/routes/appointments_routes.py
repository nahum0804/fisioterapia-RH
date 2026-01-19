# app/routes/appointments_routes.py
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from ..services.appointments_service import AppointmentsService
from ..models import Appointment
from ..utils.auth_required import auth_required, admin_required
from datetime import timedelta

bp = Blueprint("appointments", __name__)
from app.services.planner_service import PlannerService

# --------------------- User porpouse functionality ----------------------------

# horario: Lun-Vie 13:00-19:00 (último inicio 18:00)
OPEN_HOUR = 13
CLOSE_HOUR = 19

def is_weekday(dt: datetime):
    return dt.weekday() < 5  # 0..4

def in_business_hours(start: datetime, end: datetime):
    # start/end deben ser TZ-aware
    if not is_weekday(start):
        return False
    if start.date() != end.date():
        return False
    # horas válidas: [13:00, 19:00] con end <= 19:00
    if start.hour < OPEN_HOUR:
        return False
    if end.hour > CLOSE_HOUR or (end.hour == CLOSE_HOUR and end.minute > 0):
        return False
    return True

@bp.get("/availability")
@auth_required
def availability():
    date_from = parse_dt(request.args.get("from"))
    date_to = parse_dt(request.args.get("to"))
    if not date_from or not date_to:
        return jsonify({"error": "from and to are required (ISO)"}), 400

    # generamos slots de 1h por día
    ONE_HOUR = timedelta(hours=1)
    slots = []

    cursor = date_from
    # normalizamos cursor al inicio del día en su tz
    cursor = cursor.replace(hour=0, minute=0, second=0, microsecond=0)

    while cursor < date_to:
        if is_weekday(cursor):
            for h in range(OPEN_HOUR, CLOSE_HOUR):  # 13..18
                start = cursor.replace(hour=h, minute=0, second=0, microsecond=0)
                end = start + ONE_HOUR

                # fuera del rango pedido
                if start < date_from or end > date_to:
                    continue

                # si hay conflicto con agenda => no disponible
                if PlannerService.has_conflict(start, end):
                    continue

                slots.append(start.isoformat())

        cursor = cursor + timedelta(days=1)

    return jsonify({"duration_min": 60, "slots": slots}), 200

# --------------------- Endpoints appointments ----------------------------

def parse_dt(value: str | None):
    if not value:
        return None
    try:
        value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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

    description = (payload.get("description") or "").strip()
    if not description:
        return jsonify({"error": "description is required"}), 400

    proposed_starts = payload.get("proposed_starts")
    if not isinstance(proposed_starts, list) or len(proposed_starts) != 3:
        return jsonify({"error": "proposed_starts must be an array of 3 ISO datetimes"}), 400

    starts = []
    for s in proposed_starts:
        dt = parse_dt(s)
        if not dt:
            return jsonify({"error": "Invalid datetime in proposed_starts"}), 400
        starts.append(dt)

    appt = AppointmentsService.request_appointment_with_proposals({
        "user_id": g.user_id,
        "description": description,
        "comment": payload.get("comment"),
        "considerations": payload.get("considerations"),
        "starts": starts,
    })

    return jsonify(appt.to_dict()), 201


@bp.post("/<uuid:appointment_id>/confirm")
@auth_required
@admin_required
def confirm_appointment(appointment_id):
    payload = request.get_json(force=True) or {}

    proposal_id = payload.get("proposal_id")
    scheduled_start = parse_dt(payload.get("scheduled_start"))

    try:
        if proposal_id:
            appt = AppointmentsService.admin_confirm_from_proposal(appointment_id, proposal_id)
        else:
            if not scheduled_start:
                return jsonify({"error": "scheduled_start or proposal_id is required"}), 400
            appt = AppointmentsService.admin_confirm(appointment_id, scheduled_start)

        return jsonify(appt.to_dict()), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400



# (Compatibilidad) marcar pagado con POST sin payload
@bp.post("/<uuid:appointment_id>/mark-paid")
@auth_required
@admin_required
def mark_paid(appointment_id):
    appt = AppointmentsService.mark_paid(appointment_id)
    return jsonify(appt.to_dict()), 200


# ✅ NUEVO: set-paid para editar pago (pagado / no pagado)
@bp.post("/<uuid:appointment_id>/set-paid")
@auth_required
@admin_required
def set_paid(appointment_id):
    payload = request.get_json(force=True) or {}

    if "is_paid" not in payload:
        return jsonify({"error": "is_paid is required (true/false)"}), 400

    is_paid = bool(payload.get("is_paid"))
    note = payload.get("note")  # opcional: motivo/observación

    appt = AppointmentsService.set_paid(appointment_id, is_paid=is_paid, note=note)
    return jsonify(appt.to_dict()), 200


@bp.patch("/<uuid:appointment_id>")
@auth_required
@admin_required
def admin_update_appointment(appointment_id):
    payload = request.get_json(force=True) or {}

    for k in ["requested_start", "requested_end", "scheduled_start", "scheduled_end"]:
        if k in payload:
            payload[k] = parse_dt(payload.get(k))
            if payload[k] is None and payload.get(k) is not None:
                return jsonify({"error": f"{k} must be a valid ISO date"}), 400

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


@bp.post("/<uuid:appointment_id>/cancel")
@auth_required
@admin_required
def cancel_appointment(appointment_id):
    payload = request.get_json(force=True) or {}
    reason = payload.get("reason")  # opcional

    appt = AppointmentsService.admin_cancel(appointment_id, reason=reason)
    return jsonify(appt.to_dict()), 200

# Add appointment manual

@bp.post("/manual")
@auth_required
@admin_required
def create_manual_appointment():
    payload = request.get_json(force=True) or {}

    description = (payload.get("description") or "").strip()
    if not description:
        return jsonify({"error": "description is required"}), 400

    scheduled_start = parse_dt(payload.get("scheduled_start"))
    if not scheduled_start:
        return jsonify({"error": "scheduled_start is required (valid ISO date)"}), 400

    try:
        appt = AppointmentsService.create_manual({
            "user_id": payload.get("user_id"),
            "description": description,
            "comment": payload.get("comment"),
            "considerations": payload.get("considerations"),
            "scheduled_start": scheduled_start,
        })
        return jsonify(appt.to_dict()), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
