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

    @staticmethod
    def update_profile(user_id: str, full_name: str, email: str) -> dict:
        full_name = (full_name or "").strip()
        email = (email or "").strip().lower()

        if not full_name:
            raise ValueError("full_name es requerido")
        if not email:
            raise ValueError("email es requerido")

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verificar que exista el usuario
                cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
                if not cur.fetchone():
                    raise ValueError("Usuario no encontrado")

                # Verificar email duplicado (pero permitiendo el mismo del usuario)
                cur.execute(
                    "SELECT id FROM users WHERE email = %s AND id <> %s;",
                    (email, user_id),
                )
                if cur.fetchone():
                    raise ValueError("Ese email ya está en uso")

                cur.execute(
                    """
                    UPDATE users
                    SET full_name = %s,
                        email = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, full_name, email, role, is_active, created_at, updated_at;
                    """,
                    (full_name, email, user_id),
                )
                user = cur.fetchone()
                conn.commit()
                return user
        finally:
            conn.close()

    @staticmethod
    def change_password(user_id: str, current_password: str, new_password: str) -> None:
        if not current_password or not new_password:
            raise ValueError("current_password y new_password son requeridos")

        if len(new_password) < 6:
            raise ValueError("La nueva contraseña debe tener al menos 6 caracteres")

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT password_hash, is_active FROM users WHERE id = %s;",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Usuario no encontrado")

                if not row["is_active"]:
                    raise ValueError("Usuario inactivo")

                if not check_password_hash(row["password_hash"], current_password):
                    raise ValueError("Contraseña actual incorrecta")

                new_hash = generate_password_hash(new_password)

                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (new_hash, user_id),
                )
                conn.commit()
        finally:
            conn.close()