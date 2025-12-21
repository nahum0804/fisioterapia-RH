import uuid
from datetime import datetime, date
from sqlalchemy.dialects.postgresql import UUID
from ..extensions import db

class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    owner_user_id = db.Column(db.BigInteger, nullable=True)

    full_name = db.Column(db.Text, nullable=False)
    relation_to_booker = db.Column(db.Text, nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": str(self.id),
            "owner_user_id": self.owner_user_id,
            "full_name": self.full_name,
            "relation_to_booker": self.relation_to_booker,
            "birth_date": self.birth_date.isoformat() if isinstance(self.birth_date, date) else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
