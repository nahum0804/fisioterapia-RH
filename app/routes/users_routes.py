from flask import Blueprint, jsonify
from ..models import User

bp = Blueprint("users", __name__)

@bp.get("/")
def list_users():
    users = User.query.order_by(User.full_name.asc()).all()
    return jsonify([{
        "id": str(u.id),
        "full_name": u.full_name,
        "email": u.email,
    } for u in users]), 200
