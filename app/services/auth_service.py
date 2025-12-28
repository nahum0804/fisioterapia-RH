import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor
from app.db import get_connection
from app.services.email_service import send_email

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

    @staticmethod
    def _hash_reset_token(raw_token: str) -> str:
        pepper = os.getenv("RESET_TOKEN_PEPPER", "")
        return hashlib.sha256((raw_token + pepper).encode("utf-8")).hexdigest()

    @staticmethod
    def forgot_password(email: str) -> None:
        if not email:
            raise ValueError("email es requerido")

        email = email.strip().lower()

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, email, full_name, is_active FROM users WHERE email = %s;",
                    (email,),
                )
                user = cur.fetchone()

                if not user or not user["is_active"]:
                    return

                raw_token = secrets.token_urlsafe(32)
                token_hash = AuthService._hash_reset_token(raw_token)

                expires_minutes = int(os.getenv("RESET_TOKEN_EXPIRES_MINUTES", "30"))
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

                cur.execute(
                    """
                    UPDATE users
                    SET password_reset_token_hash = %s,
                        password_reset_expires_at = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (token_hash, expires_at, str(user["id"])),
                )
                conn.commit()

                frontend = os.getenv("FRONTEND_URL", "http://localhost:5173")
                reset_link = f"{frontend}/reset-password?token={raw_token}&email={email}"

                subject = "Recuperación de contraseña — Fisioterapia RH"

                html = f"""
                <div style="font-family:Arial, sans-serif; line-height:1.5;">
                  <h2>Fisioterapia RH</h2>
                  <p>Hola {user.get("full_name", "")},</p>
                  <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta.</p>
                  <p>Si fuiste tú, por favor accedé al siguiente enlace seguro para crear una nueva contraseña:</p>
                  <p><a href="{reset_link}" target="_blank" rel="noopener noreferrer">Restablecer contraseña</a></p>
                  <p>Este enlace expira en <b>{expires_minutes} minutos</b>.</p>
                  <p>Si no solicitaste este cambio, podés ignorar este correo. Tu contraseña no será modificada.</p>
                  <hr/>
                  <p style="font-size:12px; color:#666;">Mensaje automático — no respondas a este correo.</p>
                </div>
                """

                text = (
                    "Fisioterapia RH\n\n"
                    "Recibimos una solicitud para restablecer tu contraseña.\n"
                    f"Usa este enlace seguro (expira en {expires_minutes} minutos):\n{reset_link}\n\n"
                    "Si no fuiste tú, ignorá este correo.\n"
                )

                send_email(to_email=email, subject=subject, html_body=html, text_body=text)

        finally:
            conn.close()

    @staticmethod
    def reset_password(email: str, token: str, new_password: str) -> None:
        if not email or not token or not new_password:
            raise ValueError("email, token y new_password son requeridos")

        email = email.strip().lower()

        if len(new_password) < 8:
            raise ValueError("La nueva contraseña debe tener al menos 8 caracteres")

        token_hash = AuthService._hash_reset_token(token)

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, password_hash, password_reset_token_hash, password_reset_expires_at, is_active
                    FROM users
                    WHERE email = %s;
                    """,
                    (email,),
                )
                user = cur.fetchone()
                if not user or not user["is_active"]:
                    raise ValueError("Token inválido o expirado")

                if not user["password_reset_token_hash"] or not user["password_reset_expires_at"]:
                    raise ValueError("Token inválido o expirado")

                now = datetime.now(timezone.utc)
                expires_at = user["password_reset_expires_at"]
                # psycopg2 normalmente trae aware datetime si la columna es timestamptz
                if expires_at < now:
                    raise ValueError("Token inválido o expirado")

                if user["password_reset_token_hash"] != token_hash:
                    raise ValueError("Token inválido o expirado")

                # regla extra: no permitir que sea la misma que la anterior
                if check_password_hash(user["password_hash"], new_password):
                    raise ValueError("La nueva contraseña no puede ser igual a la anterior")

                new_hash = generate_password_hash(new_password)

                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s,
                        password_reset_token_hash = NULL,
                        password_reset_expires_at = NULL,
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (new_hash, str(user["id"])),
                )
                conn.commit()
        finally:
            conn.close()