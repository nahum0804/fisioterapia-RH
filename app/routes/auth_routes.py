from flask import Blueprint, jsonify

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/login", methods=["GET"])
def login():
    return jsonify(message="Login endpoint activo")
