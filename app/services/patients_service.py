from ..extensions import db
from ..models import Patient

class PatientsService:
    @staticmethod
    def create_patient(payload: dict) -> Patient:
        patient = Patient(
            owner_user_id=payload.get("owner_user_id"),
            full_name=payload["full_name"],
            relation_to_booker=payload.get("relation_to_booker"),
            birth_date=payload.get("birth_date"),
            notes=payload.get("notes"),
        )
        db.session.add(patient)
        db.session.commit()
        return patient

    @staticmethod
    def list_patients(owner_user_id: int | None = None) -> list[Patient]:
        q = Patient.query
        if owner_user_id is not None:
            q = q.filter(Patient.owner_user_id == owner_user_id)
        return q.order_by(Patient.created_at.desc()).all()
