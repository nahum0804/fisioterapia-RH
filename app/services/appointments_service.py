from datetime import datetime
from ..extensions import db
from ..models import Appointment, AppointmentEvent


class AppointmentsService:

    @staticmethod
    def request_appointment(payload: dict) -> Appointment:
        appt = Appointment(
            user_id=payload["user_id"], 
            description=payload["description"],
            comment=payload.get("comment"),
            considerations=payload.get("considerations"),
            requested_start=payload.get("requested_start"),
            requested_end=payload.get("requested_end"),
            status="requested",
        )

        db.session.add(appt)
        db.session.flush()  # asegura appt.id

        db.session.add(
            AppointmentEvent(
                appointment_id=appt.id,
                event_type="created",
                note="Appointment requested by patient",
            )
        )

        db.session.commit()
        return appt

    @staticmethod
    def admin_confirm(appointment_id, scheduled_start, scheduled_end) -> Appointment:
        appt = Appointment.query.get_or_404(appointment_id)

        old_status = appt.status
        appt.status = "confirmed"
        appt.scheduled_start = scheduled_start
        appt.scheduled_end = scheduled_end
        appt.updated_at = datetime.utcnow()

        db.session.add(
            AppointmentEvent(
                appointment_id=appt.id,
                event_type="status_changed",
                old_value=old_status,
                new_value="confirmed",
                note="Confirmed by therapist/admin",
            )
        )

        db.session.commit()
        return appt

    @staticmethod
    def mark_paid(appointment_id) -> Appointment:
        appt = Appointment.query.get_or_404(appointment_id)

        appt.is_paid = True
        appt.paid_at = datetime.utcnow()
        appt.updated_at = datetime.utcnow()

        db.session.add(
            AppointmentEvent(
                appointment_id=appt.id,
                event_type="payment_marked",
                old_value="unpaid",
                new_value="paid",
                note="Marked as paid manually by therapist/admin",
            )
        )

        db.session.commit()
        return appt

    @staticmethod
    def list_appointments(status=None, user_id=None):
        q = Appointment.query

        if status:
            q = q.filter(Appointment.status == status)

        if user_id:
            q = q.filter(Appointment.user_id == user_id)

        return q.order_by(Appointment.created_at.desc()).all()