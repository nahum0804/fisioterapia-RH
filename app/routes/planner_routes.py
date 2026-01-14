from flask import Blueprint, request, jsonify
from datetime import datetime
from ..extensions import db
from ..services.planner_service import PlannerService
from ..models import Appointment, PlannerItem

bp = Blueprint("planner", __name__)

def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

# =========================
# GET /api/planner?from=...&to=...&kind=...
# =========================
@bp.route("", methods=["GET"])
@bp.route("/", methods=["GET"])
def list_planner_items():
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


# =========================
# POST /api/planner  (crear evento)
# Body:
# {
#   "title": "Reunión",
#   "note": "...",
#   "start_at": "2026-01-14T18:00:00-06:00"  ó con Z
#   "end_at":   "2026-01-14T19:00:00-06:00",
#   "all_day": false,
#   "location": "..."
# }
# =========================
@bp.route("", methods=["POST"])
@bp.route("/", methods=["POST"])
def create_planner_item():
    payload = request.get_json(force=True) or {}

    start_at = parse_dt(payload.get("start_at"))
    end_at = parse_dt(payload.get("end_at"))

    if not start_at or not end_at:
        return jsonify({"error": "start_at and end_at are required (ISO)"}), 400
    if end_at <= start_at:
        return jsonify({"error": "end_at must be greater than start_at"}), 400

    title = (payload.get("title") or "").strip()
    note = payload.get("note")
    location = payload.get("location")
    all_day = bool(payload.get("all_day", False))

    # 👇 OJO: este valor debe existir en tu enum planner_item_kind
    kind_value = "event"

    item = PlannerItem(
        kind=kind_value,
        title=title,
        note=note,
        start_at=start_at,
        end_at=end_at,
        all_day=all_day,
        location=location,
        created_by=None,       # si luego querés, aquí ponés user_id del token
        appointment_id=None,   # evento NO es cita
    )

    db.session.add(item)
    db.session.commit()

    return jsonify(item.to_dict()), 201
