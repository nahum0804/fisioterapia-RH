# app/routes/users_routes.py
from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor
from app.db import get_connection
from app.utils.auth_required import auth_required, admin_required

bp = Blueprint("users", __name__, url_prefix="/api/users")

@bp.get("/")
@auth_required
@admin_required
def list_users():
    q = (request.args.get("search") or "").strip().lower()
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if q:
                cur.execute("""
                    SELECT id, full_name, email, role, is_active
                    FROM users
                    WHERE LOWER(full_name) LIKE %s OR LOWER(email) LIKE %s
                    ORDER BY full_name ASC
                    LIMIT 50;
                """, (f"%{q}%", f"%{q}%"))
            else:
                cur.execute("""
                    SELECT id, full_name, email, role, is_active
                    FROM users
                    ORDER BY full_name ASC
                    LIMIT 50;
                """)
            return jsonify({"users": cur.fetchall()}), 200
    finally:
        conn.close()
