# app/models/appointment.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from ..extensions import db
from app.utils.appointments_fields import unpack_fields


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Puede ser NULL para citas manuales sin cuenta
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", backref="appointments", lazy=True)

    # Existe en tu BD (según tu CSV). Puede quedar NULL.
    description = db.Column(db.Text, nullable=True)

    # Aquí estás guardando el "pack_fields(...)" (JSON string) o el formato viejo.
    comment = db.Column(db.Text, nullable=True)

    requested_start = db.Column(db.DateTime(timezone=True), nullable=True)
    requested_end = db.Column(db.DateTime(timezone=True), nullable=True)

    scheduled_start = db.Column(db.DateTime(timezone=True), nullable=True)
    scheduled_end = db.Column(db.DateTime(timezone=True), nullable=True)

    # En tu BD es USER-DEFINED (ENUM). En SQLAlchemy lo dejas como Text si ya te funciona.
    status = db.Column(db.Text, nullable=False, default="requested")

    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def to_dict(self):
        """
        Devuelve campos limpios para el frontend.

        - description/comment/considerations se obtienen desde self.comment usando unpack_fields
          (porque AppointmentsService usa pack_fields).
        - Si por alguna razón self.comment está vacío, cae a self.description (columna) como respaldo.
        """
        fields = unpack_fields(self.comment)

        description = (fields.get("description") or "").strip()
        user_comment = fields.get("comment")
        considerations = fields.get("considerations")

        # Fallback: si no hay description en el pack, usa la columna description si existe
        if not description and self.description:
            description = self.description

        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,

            # ✅ ya desempaquetado (lo que el frontend espera ver)
            "description": description,
            "comment": user_comment,
            "considerations": considerations,

            "requested_start": self.requested_start.isoformat() if self.requested_start else None,
            "requested_end": self.requested_end.isoformat() if self.requested_end else None,
            "scheduled_start": self.scheduled_start.isoformat() if self.scheduled_start else None,
            "scheduled_end": self.scheduled_end.isoformat() if self.scheduled_end else None,

            "status": self.status,
            "is_paid": self.is_paid,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,

            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,

            "user": {"full_name": self.user.full_name} if self.user else None,
        }
