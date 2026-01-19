# app/models/appointment_proposal.py
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from ..extensions import db

class AppointmentProposal(db.Model):
    __tablename__ = "appointment_proposals"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    appointment_id = db.Column(UUID(as_uuid=True), db.ForeignKey("appointments.id"), nullable=False)

    start_at = db.Column(db.DateTime(timezone=True), nullable=False)
    end_at = db.Column(db.DateTime(timezone=True), nullable=False)

    rank = db.Column(db.Integer, nullable=False)  # 1..3
    is_selected = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": str(self.id),
            "appointment_id": str(self.appointment_id),
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "rank": self.rank,
            "is_selected": self.is_selected,
        }
