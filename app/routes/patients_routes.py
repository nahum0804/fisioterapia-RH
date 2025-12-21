from flask import Blueprint, request, jsonify
from datetime import date

from ..services.patients_service import PatientsService

bp = Blueprint("patients", __name__)

@bp.get("/")
def list_patients():
    owner_user_id = request.args.get("owner_user_id", type=int)
    patients = PatientsService.list_patients(owner_user_id=owner_user_id)
    return jsonify([p.to_dict() for p in patients]), 200

@bp.post("/")
def create_patient():
    payload = request.get_json(force=True)

    # "YYYY-MM-DD"
    if payload.get("birth_date"):
        payload["birth_date"] = date.fromisoformat(payload["birth_date"])

    patient = PatientsService.create_patient(payload)
    return jsonify(patient.to_dict()), 201
