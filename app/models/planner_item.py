# app/models/planner_item.py
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from ..extensions import db

class PlannerItem(db.Model):
    __tablename__ = "planner_items"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # enum en DB, pero lo guardamos como string aquí (simple)
    kind = db.Column(db.Text, nullable=False, default="event")  # event | manual_appointment | block

    title = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text, nullable=True)

    start_at = db.Column(db.DateTime(timezone=True), nullable=False)
    end_at = db.Column(db.DateTime(timezone=True), nullable=False)

    all_day = db.Column(db.Boolean, nullable=False, default=False)
    location = db.Column(db.Text, nullable=True)

    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=True)
    appointment_id = db.Column(UUID(as_uuid=True), db.ForeignKey("appointments.id"), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": str(self.id),
            "kind": self.kind,
            "title": self.title,
            "note": self.note,
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "all_day": self.all_day,
            "location": self.location,
            "created_by": str(self.created_by) if self.created_by else None,
            "appointment_id": str(self.appointment_id) if self.appointment_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
