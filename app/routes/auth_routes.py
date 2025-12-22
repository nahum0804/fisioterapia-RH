from flask import Blueprint, request, jsonify, g

from app.services.auth_service import AuthService
from app.services.jwt_service import create_access_token
from app.utils.auth_required import auth_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    try:
        user = AuthService.register(
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
        )
        return jsonify({"message": "Usuario creado", "user": user}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    try:
        user = AuthService.authenticate(
            email=data.get("email", ""),
            password=data.get("password", ""),
        )
        token = create_access_token(
            user_id=str(user["id"]),
            email=user["email"],
            role=user["role"],
        )
        return jsonify({
            "access_token": token,
            "token_type": "Bearer",
            "expires_in_minutes":  int(__import__("os").getenv("JWT_EXPIRES_MINUTES", "480")),
            "user": user
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 401


@bp.get("/me")
@auth_required
def me():
    user = AuthService.get_user_by_id(g.jwt["sub"])
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify({"user": user}), 200

