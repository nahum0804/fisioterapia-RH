from flask import Blueprint, jsonify, request
from app.services.site_service import SiteService
from app.utils.auth_required import auth_required

site_bp = Blueprint("site", __name__, url_prefix="/site")

@site_bp.get("/info")
def get_info():
    data = SiteService.get_info()
    return jsonify(data or {"info": ""})

@site_bp.put("/info")
@auth_required
def update_info():
    payload = request.get_json()
    if not payload or "info" not in payload:
        return jsonify({"error": "info es requerido"}), 400

    SiteService.update_info(payload["info"])
    return jsonify({"message": "Info actualizada correctamente"})

@site_bp.get("/location")
def get_location():
    data = SiteService.get_location()
    return jsonify(data or {"location": ""})

@site_bp.put("/location")
@auth_required
def update_location():
    payload = request.get_json()
    if not payload or "location" not in payload:
        return jsonify({"error": "location es requerido"}), 400

    SiteService.update_location(payload["location"])
    return jsonify({"message": "Ubicación actualizada correctamente"})
