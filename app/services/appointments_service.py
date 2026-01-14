from datetime import datetime, timedelta
from ..extensions import db
from ..models import Appointment, AppointmentEvent
from .planner_sync import PlannerSync

ONE_HOUR = timedelta(hours=1)

class AppointmentsService:

    @staticmethod
    def request_appointment(payload: dict) -> Appointment:
        # requested_end fijo a +1h si viene requested_start
        rs = payload.get("requested_start")
        re = rs + ONE_HOUR if rs else payload.get("requested_end")

        appt = Appointment(
            user_id=payload.get("user_id"),
            description=payload.get("description"),
            comment=payload.get("comment"),
            requested_start=rs,
            requested_end=re,
            status="requested",
        )

        db.session.add(appt)
        db.session.flush()

        db.session.add(AppointmentEvent(
            appointment_id=appt.id,
            event_type="created",
            note="Appointment requested by patient",
        ))

        db.session.commit()
        return appt

    @staticmethod
    def admin_confirm(appointment_id, scheduled_start) -> Appointment:
        appt = Appointment.query.get_or_404(appointment_id)

        old_status = appt.status
        appt.status = "confirmed"
        appt.scheduled_start = scheduled_start
        appt.scheduled_end = scheduled_start + ONE_HOUR
        appt.updated_at = datetime.utcnow()

        db.session.add(AppointmentEvent(
            appointment_id=appt.id,
            event_type="status_changed",
            old_value=old_status,
            new_value="confirmed",
            note="Confirmed by therapist/admin",
        ))

        PlannerSync.upsert_for_appointment(appt)

        db.session.commit()
        return appt

    @staticmethod
    def create_manual(payload: dict) -> Appointment:
        # status confirmed directo
        ss = payload.get("scheduled_start")
        appt = Appointment(
            user_id=payload.get("user_id"),  # puede ser None
            description=payload.get("description") or "Cita",
            comment=payload.get("comment"),
            scheduled_start=ss,
            scheduled_end=ss + ONE_HOUR,
            status="confirmed",
        )

        db.session.add(appt)
        db.session.flush()

        db.session.add(AppointmentEvent(
            appointment_id=appt.id,
            event_type="created_manual",
            note="Manual appointment created by therapist/admin",
        ))

        PlannerSync.upsert_for_appointment(appt)
        db.session.commit()
        return appt

    @staticmethod
    def update_manual(appointment_id: str, payload: dict) -> Appointment:
        appt = Appointment.query.get_or_404(appointment_id)

        if "user_id" in payload:
            appt.user_id = payload["user_id"] or None

        if "description" in payload:
            appt.description = payload["description"]

        if "comment" in payload:
            appt.comment = payload["comment"]

        if "scheduled_start" in payload and payload["scheduled_start"]:
            appt.scheduled_start = payload["scheduled_start"]
            appt.scheduled_end = payload["scheduled_start"] + ONE_HOUR

        appt.updated_at = datetime.utcnow()
        PlannerSync.upsert_for_appointment(appt)

        db.session.commit()
        return appt
    
    @staticmethod
    def list_appointments(status: str | None = None, user_id: str | None = None):
        q = Appointment.query

        if status:
            q = q.filter(Appointment.status == status)

        if user_id:
            q = q.filter(Appointment.user_id == user_id)

        # orden recomendado: primero las próximas confirmadas, luego requested, etc.
        return q.order_by(
            Appointment.scheduled_start.desc().nullslast(),
            Appointment.requested_start.desc().nullslast(),
            Appointment.created_at.desc().nullslast(),
        ).all()


    @staticmethod
    def delete_appointment(appointment_id: str):
        appt = Appointment.query.get_or_404(appointment_id)
        db.session.delete(appt)  # planner_item cae por ON DELETE CASCADE
        db.session.commit()