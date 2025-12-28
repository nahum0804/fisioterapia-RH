# app/services/planner_service.py
from datetime import datetime
from ..extensions import db
from ..models import PlannerItem

ALLOWED_KINDS = {"event", "manual_appointment", "block"}

class PlannerService:

    @staticmethod
    def list_items(date_from: datetime, date_to: datetime, kind: str | None = None):
        q = PlannerItem.query

        # items que intersectan el rango
        q = q.filter(PlannerItem.start_at <= date_to).filter(PlannerItem.end_at >= date_from)

        if kind:
            q = q.filter(PlannerItem.kind == kind)

        return q.order_by(PlannerItem.start_at.asc()).all()

    @staticmethod
    def create_item(payload: dict) -> PlannerItem:
        kind = payload.get("kind", "event")
        if kind not in ALLOWED_KINDS:
            raise ValueError("Invalid kind")

        title = (payload.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")

        start_at = payload.get("start_at")
        end_at = payload.get("end_at")
        if not start_at or not end_at:
            raise ValueError("start_at and end_at are required")

        if end_at <= start_at:
            raise ValueError("end_at must be greater than start_at")

        item = PlannerItem(
            kind=kind,
            title=title,
            note=payload.get("note"),
            start_at=start_at,
            end_at=end_at,
            all_day=bool(payload.get("all_day", False)),
            location=payload.get("location"),
            created_by=payload.get("created_by"),
            appointment_id=payload.get("appointment_id"),
        )

        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def update_item(item_id, payload: dict) -> PlannerItem:
        item = PlannerItem.query.get_or_404(item_id)

        if "kind" in payload:
            if payload["kind"] not in ALLOWED_KINDS:
                raise ValueError("Invalid kind")
            item.kind = payload["kind"]

        if "title" in payload:
            title = (payload["title"] or "").strip()
            if not title:
                raise ValueError("title is required")
            item.title = title

        if "note" in payload:
            item.note = payload.get("note")

        if "location" in payload:
            item.location = payload.get("location")

        if "all_day" in payload:
            item.all_day = bool(payload.get("all_day"))

        if "start_at" in payload:
            item.start_at = payload["start_at"]

        if "end_at" in payload:
            item.end_at = payload["end_at"]

        if item.end_at <= item.start_at:
            raise ValueError("end_at must be greater than start_at")

        item.updated_at = datetime.utcnow()
        db.session.commit()
        return item

    @staticmethod
    def delete_item(item_id):
        item = PlannerItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
