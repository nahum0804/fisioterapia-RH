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

@bp.put("/me")
@auth_required
def update_me():
    data = request.get_json(silent=True) or {}
    try:
        user = AuthService.update_profile(
            user_id=g.jwt["sub"],
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
        )
        return jsonify({"message": "Perfil actualizado", "user": user}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@bp.put("/me/password")
@auth_required
def change_password():
    data = request.get_json(silent=True) or {}
    try:
        AuthService.change_password(
            user_id=g.jwt["sub"],
            current_password=data.get("current_password", ""),
            new_password=data.get("new_password", ""),
        )
        return jsonify({"message": "Contraseña actualizada"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
import traceback

@bp.post("/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    try:
        if email:
            AuthService.forgot_password(email=email)

        return jsonify({
            "message": "Si el correo está registrado, te enviaremos un enlace para restablecer tu contraseña."
        }), 200

    except Exception as e:
        print("ERROR forgot-password:", repr(e))
        traceback.print_exc()

        # En desarrollo, devolvé el error para arreglarlo rápido:
        return jsonify({"error": "Fallo enviando correo", "detail": str(e)}), 500

    
@bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    try:
        AuthService.reset_password(
            email=data.get("email", ""),
            token=data.get("token", ""),
            new_password=data.get("new_password", ""),
        )
        return jsonify({"message": "Contraseña actualizada correctamente"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400