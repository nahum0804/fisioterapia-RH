# app/services/planner_service.py
from __future__ import annotations

from datetime import datetime
from sqlalchemy import or_
from ..extensions import db
from ..models import PlannerItem

ALLOWED_KINDS = {"event", "manual_appointment", "block"}

class PlannerService:
    @staticmethod
    def list_items(date_from, date_to, kind=None):
        q = PlannerItem.query
        q = q.filter(PlannerItem.start_at <= date_to).filter(PlannerItem.end_at >= date_from)

        if kind:
            q = q.filter(PlannerItem.kind == kind)

        return q.order_by(PlannerItem.start_at.asc()).all()

    @staticmethod
    def _require_tz(dt: datetime, field_name: str):
        # Si querés ser estricto con timezone:
        # Si tu frontend siempre manda ISO con Z u offset, esto te protege.
        if dt.tzinfo is None:
            raise ValueError(f"{field_name} must include timezone offset (ISO 8601 with Z or ±HH:MM)")

    @staticmethod
    def create_item(payload: dict) -> PlannerItem:
        kind = (payload.get("kind") or "event").strip().lower()
        if kind == "appointment":
            kind = "manual_appointment"

        if kind not in ALLOWED_KINDS:
            raise ValueError("Invalid kind")

        start_at = payload.get("start_at")
        end_at = payload.get("end_at")
        if not start_at or not end_at:
            raise ValueError("start_at and end_at are required")

        # Si querés estrictamente timezone:
        # PlannerService._require_tz(start_at, "start_at")
        # PlannerService._require_tz(end_at, "end_at")

        if end_at <= start_at:
            raise ValueError("end_at must be greater than start_at")

        title = (payload.get("title") or "").strip()
        if kind == "block" and not title:
            title = "Bloqueo"
        if kind != "block" and not title:
            raise ValueError("title is required")

        if PlannerService.has_conflict(start_at, end_at, exclude_item_id=None, exclude_appointment_id=None):
            raise ValueError("Time slot already occupied")

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

        # Calcula el NUEVO rango antes de validar conflicto
        new_start = payload.get("start_at", item.start_at)
        new_end = payload.get("end_at", item.end_at)

        # Si querés estrictamente timezone:
        # PlannerService._require_tz(new_start, "start_at")
        # PlannerService._require_tz(new_end, "end_at")

        if not new_start or not new_end:
            raise ValueError("start_at and end_at are required")

        if new_end <= new_start:
            raise ValueError("end_at must be greater than start_at")

        # Si este item está ligado a una cita, excluimos “su propia cita” (por si se re-sincroniza)
        exclude_appt_id = item.appointment_id
        if PlannerService.has_conflict(new_start, new_end, exclude_item_id=item.id, exclude_appointment_id=exclude_appt_id):
            raise ValueError("Time slot already occupied")

        if "kind" in payload and payload["kind"] is not None:
            kind = (payload["kind"] or "").strip().lower()
            if kind == "appointment":
                kind = "manual_appointment"
            if kind not in ALLOWED_KINDS:
                raise ValueError("Invalid kind")
            item.kind = kind

        if "title" in payload:
            title = (payload.get("title") or "").strip()
            if item.kind == "block" and not title:
                title = "Bloqueo"
            if item.kind != "block" and not title:
                raise ValueError("title is required")
            item.title = title

        if "note" in payload:
            item.note = payload.get("note")

        if "location" in payload:
            item.location = payload.get("location")

        if "all_day" in payload:
            item.all_day = bool(payload.get("all_day"))

        item.start_at = new_start
        item.end_at = new_end

        item.updated_at = datetime.utcnow()
        db.session.commit()
        return item

    @staticmethod
    def delete_item(item_id):
        item = PlannerItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()

    @staticmethod
    def has_conflict(start_at, end_at, exclude_item_id=None, exclude_appointment_id=None):
        q = PlannerItem.query.filter(
            PlannerItem.start_at < end_at,
            PlannerItem.end_at > start_at,
        )

        if exclude_item_id:
            q = q.filter(PlannerItem.id != exclude_item_id)

        if exclude_appointment_id:
            q = q.filter(
                or_(
                    PlannerItem.appointment_id.is_(None),
                    PlannerItem.appointment_id != exclude_appointment_id,
                )
            )

        return q.first() is not None
