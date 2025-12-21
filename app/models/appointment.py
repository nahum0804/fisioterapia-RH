import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from ..extensions import db

class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booked_by_user_id = db.Column(db.BigInteger, nullable=False)
    patient_id = db.Column(UUID(as_uuid=True), db.ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)

    description = db.Column(db.Text, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    considerations = db.Column(db.Text, nullable=True)

    requested_start = db.Column(db.DateTime(timezone=True), nullable=True)
    requested_end = db.Column(db.DateTime(timezone=True), nullable=True)

    scheduled_start = db.Column(db.DateTime(timezone=True), nullable=True)
    scheduled_end = db.Column(db.DateTime(timezone=True), nullable=True)

    status = db.Column(db.Text, nullable=False, default="requested")  

    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    patient = db.relationship("Patient", lazy="joined")

    def to_dict(self):
        return {
            "id": str(self.id),
            "booked_by_user_id": self.booked_by_user_id,
            "patient_id": str(self.patient_id),
            "patient": self.patient.to_dict() if self.patient else None,
            "description": self.description,
            "comment": self.comment,
            "considerations": self.considerations,
            "requested_start": self.requested_start.isoformat() if self.requested_start else None,
            "requested_end": self.requested_end.isoformat() if self.requested_end else None,
            "scheduled_start": self.scheduled_start.isoformat() if self.scheduled_start else None,
            "scheduled_end": self.scheduled_end.isoformat() if self.scheduled_end else None,
            "status": self.status,
            "is_paid": self.is_paid,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
