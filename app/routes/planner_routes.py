# app/routes/planner_routes.py
from __future__ import annotations

from flask import Blueprint, request, jsonify, g
from ..utils.auth_required import auth_required, admin_required
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..services.planner_service import PlannerService
from ..models import Appointment, PlannerItem  # PlannerItem para get_or_404

bp = Blueprint("planner", __name__)

def parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@bp.route("", methods=["GET", "POST"])
@bp.route("/", methods=["GET", "POST"])
@auth_required
@admin_required
def planner_root():
    if request.method == "GET":
        date_from = parse_dt(request.args.get("from"))
        date_to = parse_dt(request.args.get("to"))
        kind = request.args.get("kind")

        if not date_from or not date_to:
            return jsonify({"error": "from and to are required (ISO)"}), 400

        items = PlannerService.list_items(date_from, date_to, kind=kind)
        result = []
        for it in items:
            d = it.to_dict()
            if d.get("appointment_id"):
                appt = Appointment.query.get(it.appointment_id)
                d["appointment"] = appt.to_dict() if appt else None
            result.append(d)
        return jsonify(result), 200

    payload = request.get_json(force=True) or {}
    start_at = parse_dt(payload.get("start_at"))
    end_at = parse_dt(payload.get("end_at"))

    if not start_at or not end_at:
        return jsonify({"error": "start_at and end_at are required (ISO)"}), 400

    kind = (payload.get("kind") or "event")
    if kind == "appointment":
        kind = "manual_appointment"

    try:
        item = PlannerService.create_item({
            "kind": kind,
            "title": payload.get("title") or "",
            "note": payload.get("note"),
            "start_at": start_at,
            "end_at": end_at,
            "all_day": bool(payload.get("all_day", False)),
            "location": payload.get("location"),
            "created_by": g.user_id,
        })
        return jsonify(item.to_dict()), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
@bp.post("/blocks")
@bp.post("/blocks/")
@auth_required
@admin_required
def create_block():
    payload = request.get_json(force=True) or {}

    start_at = parse_dt(payload.get("start_at"))
    end_at = parse_dt(payload.get("end_at"))
    if not start_at or not end_at:
        return jsonify({"error": "start_at and end_at are required (ISO)"}), 400

    try:
        item = PlannerService.create_item({
            "kind": "block",
            "title": payload.get("title") or "Bloqueo",
            "note": payload.get("note"),
            "start_at": start_at,
            "end_at": end_at,
            "all_day": bool(payload.get("all_day", False)),
            "location": payload.get("location"),
            "created_by": g.user_id,
        })
        return jsonify(item.to_dict()), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    


@bp.route("/<item_id>", methods=["GET", "PUT", "DELETE"])
@bp.route("/<item_id>/", methods=["GET", "PUT", "DELETE"])
@auth_required
@admin_required
def planner_item(item_id: str):
    _ = PlannerItem.query.get_or_404(item_id)

    if request.method == "GET":
        it = PlannerItem.query.get(item_id)
        d = it.to_dict()
        if d.get("appointment_id"):
            appt = Appointment.query.get(it.appointment_id)
            d["appointment"] = appt.to_dict() if appt else None
        return jsonify(d), 200

    if request.method == "PUT":
        payload = request.get_json(force=True) or {}
        start_at = parse_dt(payload.get("start_at"))
        end_at = parse_dt(payload.get("end_at"))

        if not start_at or not end_at:
            return jsonify({"error": "start_at and end_at are required (ISO)"}), 400

        kind = payload.get("kind")
        if isinstance(kind, str):
            kind = kind.strip().lower()
            if kind == "appointment":
                kind = "manual_appointment"
        else:
            kind = None

        update_payload = {"start_at": start_at, "end_at": end_at}

        for k in ["title", "note", "location", "all_day"]:
            if k in payload:
                update_payload[k] = payload.get(k)

        if kind is not None:
            update_payload["kind"] = kind

        try:
            updated = PlannerService.update_item(item_id, update_payload)
            return jsonify(updated.to_dict()), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    try:
        PlannerService.delete_item(item_id)
        return jsonify({"ok": True}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
