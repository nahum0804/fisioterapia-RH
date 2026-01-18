# app/services/appointments_service.py
from __future__ import annotations

from datetime import timedelta

from datetime import datetime, timedelta

from ..extensions import db
from ..models import Appointment, AppointmentEvent, User
from app.utils.appointments_fields import pack_fields, unpack_fields

# ✅ Planner sync (para reflejar la cita en agenda)
from app.services.planner_sync import PlannerSync
from .planner_service import PlannerService

# ✅ Correos
from app.services.appointment_mailer import (
    email_on_request,
    email_on_confirm,
    email_on_cancel,
)

ONE_HOUR = timedelta(hours=1)

class AppointmentsService:
    @staticmethod
    def request_appointment(payload: dict) -> Appointment:
        # requested_end fijo a +1h si viene requested_start
        rs = payload.get("requested_start")
        re = rs + ONE_HOUR if rs else payload.get("requested_end")

        appt = Appointment(
            user_id=payload["user_id"],
            # Guardamos description/comment/considerations empaquetado en comment
            comment=pack_fields(
                payload.get("description") or "",
                payload.get("comment"),
                payload.get("considerations"),
            ),
            requested_start=rs,
            requested_end=re,
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

        # correo
        user = db.session.get(User, appt.user_id)
        if user and getattr(user, "email", None):
            email_on_request(
                user_email=user.email,
                user_name=getattr(user, "full_name", "Paciente"),
                appt=appt,
            )

        return appt

    @staticmethod
    def admin_confirm(appointment_id, scheduled_start):
        appt = Appointment.query.get_or_404(appointment_id)

        end = scheduled_start + ONE_HOUR
        if PlannerService.has_conflict(scheduled_start, end, exclude_appointment_id=appt.id):
            raise ValueError("Time slot already occupied")

        old_status = appt.status
        appt.status = "confirmed"
        appt.scheduled_start = scheduled_start
        appt.scheduled_end = scheduled_start + ONE_HOUR
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

        PlannerSync.upsert_for_appointment(appt)
        db.session.commit()

        # correo opcional
        user = db.session.get(User, appt.user_id)
        if user and user.email:
            email_on_confirm(
                user_email=user.email,
                user_name=user.full_name,
                appt=appt,
            )

        return appt



    @staticmethod
    def create_manual(payload: dict) -> Appointment:
        ss = payload.get("scheduled_start")
        if not ss:
            raise ValueError("scheduled_start is required")
        
        end = ss + ONE_HOUR
        if PlannerService.has_conflict(ss, end):
            raise ValueError("Time slot already occupied")

        appt = Appointment(
            user_id=payload.get("user_id"),  # puede ser None
            comment=pack_fields(
                payload.get("description") or "Cita",
                payload.get("comment"),
                payload.get("considerations"),
            ),
            scheduled_start=ss,
            scheduled_end=ss + ONE_HOUR,
            status="confirmed",
        )

        db.session.add(appt)
        db.session.flush()

        db.session.add(
            AppointmentEvent(
                appointment_id=appt.id,
                event_type="created_manual",
                note="Manual appointment created by therapist/admin",
            )
        )

        # ✅ reflejar en agenda
        PlannerSync.upsert_for_appointment(appt)

        db.session.commit()

        # correo (si tiene user asociado)
        user = db.session.get(User, appt.user_id) if appt.user_id else None
        if user and getattr(user, "email", None):
            email_on_confirm(
                user_email=user.email,
                user_name=getattr(user, "full_name", "Paciente"),
                appt=appt,
            )

        return appt


    # ✅ Legacy: si alguna ruta vieja llama mark_paid, esto NO rompe y usa set_paid por debajo
    @staticmethod
    def mark_paid(appointment_id, note: str | None = None) -> Appointment:
        """
        (Compatibilidad) Marca una cita como pagada. No permite revertir.
        Si ya tienes /set-paid, idealmente deja de usar este endpoint.
        """
        return AppointmentsService.set_paid(appointment_id, True, note=note)

    @staticmethod
    def set_paid(appointment_id, is_paid: bool, note: str | None = None) -> Appointment:
        """
        Permite editar el pago (pagado / no pagado)
        - Si is_paid=True: is_paid=True y paid_at=now
        - Si is_paid=False: is_paid=False y paid_at=None
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
    def list_appointments(status: str | None = None, user_id: str | None = None):
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
            fields.get("description") or "",
            fields.get("comment"),
            fields.get("considerations"),
        )

        for k in ["requested_start", "requested_end", "scheduled_start", "scheduled_end"]:
            if k in payload:
                setattr(appt, k, payload[k])

        appt.updated_at = datetime.utcnow()

        # ✅ si cambiaron scheduled_*, reflejar agenda
        PlannerSync.upsert_for_appointment(appt)

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

        # ✅ al cancelar, borrar/actualizar item de agenda si existe
        PlannerSync.upsert_for_appointment(appt)

        db.session.commit()

        # correo
        user = db.session.get(User, appt.user_id) if appt.user_id else None
        if user and getattr(user, "email", None):
            email_on_cancel(
                user_email=user.email,
                user_name=getattr(user, "full_name", "Paciente"),
                appt=appt,
                reason=reason,
            )

        return appt

    @staticmethod
    def delete_appointment(appointment_id) -> None:
        appt = Appointment.query.get_or_404(appointment_id)

        # ✅ limpia agenda antes de borrar
        PlannerSync.upsert_for_appointment(appt)

        db.session.delete(appt)
        db.session.commit()
