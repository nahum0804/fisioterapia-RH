# app/services/planner_sync.py
from __future__ import annotations

from datetime import datetime
from ..extensions import db
from ..models import PlannerItem, Appointment

class PlannerSync:
    @staticmethod
    def upsert_for_appointment(appt: Appointment):
        # Si no hay scheduled_start/end => no se muestra en agenda
        if not appt.scheduled_start or not appt.scheduled_end:
            item = PlannerItem.query.filter_by(appointment_id=appt.id).first()
            if item:
                db.session.delete(item)
            return None

        d = appt.to_dict()
        desc = (d.get("description") or "").strip()
        user_name = None
        try:
            user_name = d.get("user", {}).get("full_name")
        except Exception:
            user_name = None

        title = f"Cita: {user_name}" if user_name else (desc if desc else "Cita manual")
        note = (d.get("comment") or "").strip() if d.get("comment") else None

        item = PlannerItem.query.filter_by(appointment_id=appt.id).first()

        if not item:
            item = PlannerItem(
                kind="event",  # ✅ coincide con tu enum actual
                title=title,
                note=note,
                start_at=appt.scheduled_start,
                end_at=appt.scheduled_end,
                all_day=False,
                appointment_id=appt.id,
            )
            db.session.add(item)
        else:
            item.kind = "event"
            item.title = title
            item.note = note
            item.start_at = appt.scheduled_start
            item.end_at = appt.scheduled_end
            item.all_day = False

        item.updated_at = datetime.utcnow()
        return item
