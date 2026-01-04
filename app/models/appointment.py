from dataclasses import fields
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from ..extensions import db
from app.utils.appointments_fields import pack_fields, unpack_fields

class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", backref="appointments", lazy=True)

    comment = db.Column(db.Text, nullable=True)

    requested_start = db.Column(db.DateTime(timezone=True), nullable=True)
    requested_end = db.Column(db.DateTime(timezone=True), nullable=True)

    scheduled_start = db.Column(db.DateTime(timezone=True), nullable=True)
    scheduled_end = db.Column(db.DateTime(timezone=True), nullable=True)

    status = db.Column(db.Text, nullable=False, default="requested")  

    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "description": self.comment.split("\n")[0] if self.comment else "",
            "comment": self.comment.split("\n")[1] if self.comment and len(self.comment.split("\n")) > 1 else None,
            "considerations": self.comment.split("\n")[2] if self.comment and len(self.comment.split("\n")) > 2 else None,
            "requested_start": self.requested_start.isoformat() if self.requested_start else None,
            "requested_end": self.requested_end.isoformat() if self.requested_end else None,
            "scheduled_start": self.scheduled_start.isoformat() if self.scheduled_start else None,
            "scheduled_end": self.scheduled_end.isoformat() if self.scheduled_end else None,
            "status": self.status,
            "is_paid": self.is_paid,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user": {
                "full_name": self.user.full_name
            } if self.user else None,
        }
