import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from ..extensions import db

class AppointmentEvent(db.Model):
    __tablename__ = "appointment_events"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = db.Column(UUID(as_uuid=True), db.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)

    event_type = db.Column(db.Text, nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    note = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
