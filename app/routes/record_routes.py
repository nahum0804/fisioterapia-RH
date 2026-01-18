from flask import Blueprint, request, jsonify, g
from app.utils.auth_required import admin_required
from app.utils.auth_required import auth_required
from app.services.record_service import RecordService

bp = Blueprint("records", __name__, url_prefix="/api/records")

# Admin: crear expediente
@bp.post("/")
@auth_required
@admin_required
def create_record():
    data = request.get_json(silent=True) or {}
    try:
        record = RecordService.create_record(data)
        return jsonify({"record": record}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# Admin: buscar por nombre (?q=Andrea)
@bp.get("/search")
@auth_required
@admin_required
def search_records():
    q = request.args.get("q", "")
    records = RecordService.search_by_name(q)
    return jsonify({"records": records}), 200

# Admin: obtener 1 expediente
@bp.get("/<record_id>")
@auth_required
@admin_required
def get_record(record_id: str):
    record = RecordService.get_record(record_id)
    if not record:
        return jsonify({"error": "Expediente no encontrado"}), 404

    # ✅ Auto-sync: si el expediente está vinculado a un usuario, agrega citas completadas
    synced_added = 0
    try:
        user_id = record.get("user_id")
        if user_id:
            synced_added = RecordService.sync_entries_from_completed_appointments(str(record["id"]), str(user_id))
    except Exception:
        # No romper la vista del expediente si el sync falla
        synced_added = 0

    entries = RecordService.list_entries(record_id)
    return jsonify({"record": record, "entries": entries, "synced": {"added": synced_added}}), 200

# Admin: actualizar expediente
@bp.put("/<record_id>")
@auth_required
@admin_required
def update_record(record_id: str):
    data = request.get_json(silent=True) or {}
    try:
        record = RecordService.update_record(record_id, data)
        return jsonify({"record": record}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# Admin: eliminar expediente
@bp.delete("/<record_id>")
@auth_required
@admin_required
def delete_record(record_id: str):
    try:
        RecordService.delete_record(record_id)
        return jsonify({"message": "Expediente eliminado"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

# Admin: agregar diagnóstico/tratamiento
@bp.post("/<record_id>/entries")
@auth_required
@admin_required
def add_entry(record_id: str):
    data = request.get_json(silent=True) or {}
    try:
        entry = RecordService.add_entry(record_id, data)
        return jsonify({"entry": entry}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# Admin: listar entradas (por si lo ocupas separado)
@bp.get("/<record_id>/entries")
@auth_required
@admin_required
def list_entries(record_id: str):
    entries = RecordService.list_entries(record_id)
    return jsonify({"entries": entries}), 200

# Admin: obtener todos los expedientes
@bp.get("/")
@auth_required
@admin_required
def list_records():
    records = RecordService.list_all_records()
    return jsonify({"records": records}), 200


# Paciente: obtener mi expediente (si está vinculado)
@bp.get("/me")
@auth_required
def my_record():
    user_id = g.jwt["sub"]
    record = RecordService.get_my_record(user_id)
    if not record:
        return jsonify({"record": None}), 200

    # ✅ Auto-sync (mi expediente)
    synced_added = 0
    try:
        synced_added = RecordService.sync_entries_from_completed_appointments(str(record["id"]), str(user_id))
    except Exception:
        synced_added = 0

    entries = RecordService.list_entries(str(record["id"]))
    return jsonify({"record": record, "entries": entries, "synced": {"added": synced_added}}), 200


@bp.patch("/entries/<entry_id>")
@auth_required
@admin_required
def update_entry(entry_id):
    data = request.get_json(silent=True) or {}
    try:
        updated = RecordService.update_entry(entry_id, data)
        return jsonify({"entry": updated}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400