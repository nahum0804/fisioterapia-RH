from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor

from app.db import get_connection


class AuthService:
    @staticmethod
    def register(full_name: str, email: str, password: str) -> dict:
        if not full_name or not email or not password:
            raise ValueError("full_name, email y password son requeridos")

        email = email.strip().lower()
        full_name = full_name.strip()

        if len(password) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")

        password_hash = generate_password_hash(password)

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verificar si existe
                cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
                if cur.fetchone():
                    raise ValueError("El email ya está registrado")

                cur.execute(
                    """
                    INSERT INTO users (full_name, email, password_hash, role, is_active)
                    VALUES (%s, %s, %s, 'user', TRUE)
                    RETURNING id, full_name, email, role, is_active, created_at, updated_at;
                    """,
                    (full_name, email, password_hash),
                )
                user = cur.fetchone()
                conn.commit()
                return user
        finally:
            conn.close()

    @staticmethod
    def authenticate(email: str, password: str) -> dict:
        if not email or not password:
            raise ValueError("email y password son requeridos")

        email = email.strip().lower()

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, full_name, email, password_hash, role, is_active, created_at, updated_at
                    FROM users
                    WHERE email = %s;
                    """,
                    (email,),
                )
                user = cur.fetchone()

                if not user:
                    raise ValueError("Credenciales inválidas")

                if not user["is_active"]:
                    raise ValueError("Usuario inactivo")

                if not check_password_hash(user["password_hash"], password):
                    raise ValueError("Credenciales inválidas")

                # Nunca devolvemos el hash hacia afuera
                user.pop("password_hash", None)
                return user
        finally:
            conn.close()
    
    @staticmethod
    def get_user_by_id(user_id: str) -> dict | None:
        from psycopg2.extras import RealDictCursor
        from app.db import get_connection

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, full_name, email, role, is_active, created_at, updated_at
                    FROM users
                    WHERE id = %s;
                """, (user_id,))
                return cur.fetchone()
        finally:
            conn.close()
