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
        return fn(*args, **kwargs)

    return wrapper
