# app/services/appointments_service.py
from datetime import datetime

from ..extensions import db
from ..models import Appointment, AppointmentEvent, User
from app.utils.appointments_fields import pack_fields, unpack_fields

# Correos
from app.services.appointment_mailer import (
    email_on_request,
    email_on_confirm,
    email_on_cancel,
)


class AppointmentsService:

    @staticmethod
    def request_appointment(payload: dict) -> Appointment:
        appt = Appointment(
            user_id=payload["user_id"],
            comment=pack_fields(
                payload["description"],
                payload.get("comment"),
                payload.get("considerations")
            ),
            requested_start=payload.get("requested_start"),
            requested_end=payload.get("requested_end"),
            status="requested",
        )

        db.session.add(appt)
        db.session.flush()

        db.session.add(
            AppointmentEvent(
                appointment_id=appt.id,
                event_type="created",
                note="Appointment requested by patient",
            )
        )

        db.session.commit()

        user = db.session.get(User, appt.user_id)
        if user and getattr(user, "email", None):
            email_on_request(
                user_email=user.email,
                user_name=getattr(user, "full_name", "Paciente"),
                appt=appt
            )

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

        user = db.session.get(User, appt.user_id)
        if user and getattr(user, "email", None):
            email_on_confirm(
                user_email=user.email,
                user_name=getattr(user, "full_name", "Paciente"),
                appt=appt
            )

        return appt

    @staticmethod
    def mark_paid(appointment_id) -> Appointment:
        """
        (Compatibilidad) Marca una cita como pagada. No permite revertir.
        """
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
    def set_paid(appointment_id, is_paid: bool, note: str | None = None) -> Appointment:
        """
        ✅ Nuevo: Permite editar el pago (pagado / no pagado)
        - Si is_paid=True: set is_paid y paid_at=now
        - Si is_paid=False: set is_paid y paid_at=None
        Registra AppointmentEvent.
        """
        appt = Appointment.query.get_or_404(appointment_id)

        old_value = "paid" if appt.is_paid else "unpaid"
        new_value = "paid" if is_paid else "unpaid"

        appt.is_paid = is_paid
        appt.paid_at = datetime.utcnow() if is_paid else None
        appt.updated_at = datetime.utcnow()

        db.session.add(
            AppointmentEvent(
                appointment_id=appt.id,
                event_type="payment_updated",
                old_value=old_value,
                new_value=new_value,
                note=note or "Payment status updated by therapist/admin",
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

    @staticmethod
    def admin_update(appointment_id, payload: dict) -> Appointment:
        appt = Appointment.query.get_or_404(appointment_id)

        fields = unpack_fields(appt.comment)

        if "description" in payload:
            fields["description"] = payload.get("description") or ""
        if "comment" in payload:
            fields["comment"] = payload.get("comment")
        if "considerations" in payload:
            fields["considerations"] = payload.get("considerations")

        appt.comment = pack_fields(
            fields["description"],
            fields["comment"],
            fields["considerations"]
        )

        for k in ["requested_start", "requested_end", "scheduled_start", "scheduled_end"]:
            if k in payload:
                setattr(appt, k, payload[k])

        appt.updated_at = datetime.utcnow()
        db.session.commit()
        return appt

    @staticmethod
    def admin_cancel(appointment_id, reason: str | None = None) -> Appointment:
        appt = Appointment.query.get_or_404(appointment_id)

        old_status = appt.status
        appt.status = "cancelled"
        appt.updated_at = datetime.utcnow()

        db.session.add(
            AppointmentEvent(
                appointment_id=appt.id,
                event_type="status_changed",
                old_value=old_status,
                new_value="cancelled",
                note=reason or "Cancelled by therapist/admin",
            )
        )

        db.session.commit()

        user = db.session.get(User, appt.user_id)
        if user and getattr(user, "email", None):
            email_on_cancel(
                user_email=user.email,
                user_name=getattr(user, "full_name", "Paciente"),
                appt=appt,
                reason=reason
            )

        return appt

    @staticmethod
    def delete_appointment(appointment_id) -> None:
        appt = Appointment.query.get_or_404(appointment_id)
        db.session.delete(appt)
        db.session.commit()
