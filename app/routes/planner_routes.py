# app/routes/planner_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..services.planner_service import PlannerService

bp = Blueprint("planner", __name__)

def parse_dt(value: str | None):
    if not value:
        return None
    # acepta ISO: "2025-12-28T09:00:00.000Z"
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

@bp.get("/")
def list_planner_items():
    date_from = parse_dt(request.args.get("from"))
    date_to = parse_dt(request.args.get("to"))
    kind = request.args.get("kind")

    if not date_from or not date_to:
        return jsonify({"error": "from and to are required (ISO)"}), 400

    items = PlannerService.list_items(date_from, date_to, kind=kind)
    return jsonify([i.to_dict() for i in items]), 200

@bp.post("/")
def create_planner_item():
    payload = request.get_json(force=True)

    payload["start_at"] = parse_dt(payload.get("start_at"))
    payload["end_at"] = parse_dt(payload.get("end_at"))

    try:
        item = PlannerService.create_item(payload)
        return jsonify(item.to_dict()), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.put("/<uuid:item_id>")
def update_planner_item(item_id):
    payload = request.get_json(force=True)

    if "start_at" in payload:
        payload["start_at"] = parse_dt(payload.get("start_at"))
    if "end_at" in payload:
        payload["end_at"] = parse_dt(payload.get("end_at"))

    try:
        item = PlannerService.update_item(item_id, payload)
        return jsonify(item.to_dict()), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.delete("/<uuid:item_id>")
def delete_planner_item(item_id):
    PlannerService.delete_item(item_id)
    return jsonify({"ok": True}), 200
