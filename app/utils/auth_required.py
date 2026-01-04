from functools import wraps
from flask import request, jsonify, g
import jwt

from app.services.jwt_service import decode_token


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Falta Authorization: Bearer <token>"}), 401

        token = auth.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401

        # Guardamos info del usuario en g (global request context)
        g.jwt = payload
        g.user_id = payload.get("sub")
        g.email = payload.get("email")
        g.role = payload.get("role")

        if not g.user_id or not g.role:
            return jsonify({"error": "Token inválido (faltan claims)"}), 401

        return fn(*args, **kwargs)

    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        role = getattr(g, "role", None) or (g.jwt.get("role") if hasattr(g, "jwt") else None)
        if role != "admin":
            return jsonify({"error": "No autorizado (admin requerido)"}), 403
        return fn(*args, **kwargs)
    return wrapper
