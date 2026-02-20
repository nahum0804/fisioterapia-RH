import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from psycopg2.extras import RealDictCursor

from app.db import get_connection
from app.utils.appointments_fields import unpack_fields

class RecordService:
    CR_TZ = ZoneInfo("America/Costa_Rica")

    @staticmethod
    def _to_cr_date(dt) -> str:
        """Convierte un datetime (idealmente timezone-aware) a fecha YYYY-MM-DD en CR."""
        if not dt:
            # Fallback: hoy
            return datetime.now(tz=RecordService.CR_TZ).date().isoformat()

        # psycopg2 suele devolver aware; si llega naive, asumimos UTC.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))

        return dt.astimezone(RecordService.CR_TZ).date().isoformat()

    @staticmethod
    def sync_entries_from_completed_appointments(record_id: str, user_id: str) -> int:
        """
        Crea automáticamente entradas de expediente por cada cita que cumpla:
        - status = confirmed
        - is_paid = true
        - scheduled_end ya pasó
        y que aún no exista en record_entries (por appointment_id).

        Requiere que record_entries tenga columna appointment_id (UUID) con UNIQUE.
        """
        if not record_id or not user_id:
            return 0

        conn = get_connection()
        inserted = 0
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Traer citas completadas y pagadas que aún no estén registradas
                cur.execute(
                    """
                    SELECT
                        a.id,
                        a.scheduled_start,
                        a.scheduled_end,
                        a.comment,
                        a.description
                    FROM appointments a
                    WHERE a.user_id = %s
                      AND a.status = 'confirmed'
                      AND a.is_paid = true
                      AND a.scheduled_end IS NOT NULL
                      AND a.scheduled_end < NOW()
                      AND NOT EXISTS (
                        SELECT 1
                        FROM record_entries re
                        WHERE re.appointment_id = a.id
                      )
                    ORDER BY a.scheduled_end ASC;
                    """,
                    (user_id,),
                )

                appts = cur.fetchall() or []
                if not appts:
                    return 0

                for a in appts:
                    fields = unpack_fields(a.get("comment"))
                    desc = (fields.get("description") or a.get("description") or "Cita").strip()

                    # Mapeo razonable a campos del expediente
                    diagnosis = f"Cita: {desc}".strip()

                    parts = []
                    if fields.get("comment"):
                        parts.append(f"Notas: {str(fields.get('comment')).strip()}")
                    if fields.get("considerations"):
                        parts.append(f"Consideraciones: {str(fields.get('considerations')).strip()}")
                    treatment = "\n".join(parts).strip() or "Pendiente de completar por el terapeuta."

                    entry_date = RecordService._to_cr_date(a.get("scheduled_start") or a.get("scheduled_end"))

                    cur.execute(
                        """
                        INSERT INTO record_entries
                          (record_id, entry_date, diagnosis, treatment, is_current, appointment_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (appointment_id) DO NOTHING;
                        """,
                        (
                            record_id,
                            entry_date,
                            diagnosis,
                            treatment,
                            False,
                            a["id"],
                        ),
                    )
                    inserted += cur.rowcount

                conn.commit()
                return inserted
        finally:
            conn.close()
    # Crear expediente
    @staticmethod
    def _resolve_user_id_by_email(cur, user_email: str | None):
        if not user_email:
            return None

        email = user_email.strip().lower()
        cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
        row = cur.fetchone()
        if not row:
            raise ValueError("No existe un usuario con ese correo para vincular")
        return row["id"]

    @staticmethod
    def create_record(payload: dict) -> dict:
        required = ["patient_name", "patient_age", "phone"]
        for k in required:
            if payload.get(k) in (None, ""):
                raise ValueError(f"{k} es requerido")

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                user_email = payload.get("user_email")
                user_id = RecordService._resolve_user_id_by_email(cur, user_email)  # ✅ aquí

                cur.execute("""
                    INSERT INTO patient_records
                      (patient_name, patient_age, phone, extra_description, user_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *;
                """, (
                    payload["patient_name"].strip(),
                    int(payload["patient_age"]),
                    payload["phone"].strip(),
                    payload.get("extra_description"),
                    user_id
                ))
                record = cur.fetchone()
                conn.commit()
                return record
        finally:
            conn.close()


    # Buscar por nombre 
    @staticmethod
    def search_by_name(q: str) -> list[dict]:
        q = (q or "").strip()
        if not q:
            return []

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM patient_records
                    WHERE patient_name ILIKE %s
                    ORDER BY patient_name ASC, created_at DESC;
                """, (f"%{q}%",))
                return cur.fetchall()
        finally:
            conn.close()

    # Obtener expediente por id (admin)
    @staticmethod
    def get_record(record_id: str) -> dict | None:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        pr.*,
                        u.email AS user_email
                    FROM patient_records pr
                    LEFT JOIN users u ON u.id = pr.user_id
                    WHERE pr.id = %s;
                """, (record_id,))
                record = cur.fetchone()
                return record
        finally:
            conn.close()


    # Modificar expediente (admin)
    @staticmethod
    def update_record(record_id: str, payload: dict) -> dict:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM patient_records WHERE id = %s;", (record_id,))
                if not cur.fetchone():
                    raise ValueError("Expediente no encontrado")

                # si viene el campo user_email, decidir vínculo
                user_id = None
                if "user_email" in payload:
                    user_email = payload.get("user_email")
                    if user_email in (None, ""):
                        user_id = None  # desvincular
                    else:
                        user_id = RecordService._resolve_user_id_by_email(cur, user_email)

                    cur.execute("""
                        UPDATE patient_records
                        SET patient_name = COALESCE(%s, patient_name),
                            patient_age = COALESCE(%s, patient_age),
                            phone = COALESCE(%s, phone),
                            extra_description = COALESCE(%s, extra_description),
                            user_id = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING *;
                    """, (
                        payload.get("patient_name"),
                        payload.get("patient_age"),
                        payload.get("phone"),
                        payload.get("extra_description"),
                        user_id,
                        record_id
                    ))
                else:
                    # si no mandan user_email, no tocar user_id
                    cur.execute("""
                        UPDATE patient_records
                        SET patient_name = COALESCE(%s, patient_name),
                            patient_age = COALESCE(%s, patient_age),
                            phone = COALESCE(%s, phone),
                            extra_description = COALESCE(%s, extra_description),
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING *;
                    """, (
                        payload.get("patient_name"),
                        payload.get("patient_age"),
                        payload.get("phone"),
                        payload.get("extra_description"),
                        record_id
                    ))

                updated = cur.fetchone()
                conn.commit()
                return updated
        finally:
            conn.close()


    # Eliminar expediente (admin)
    @staticmethod
    def delete_record(record_id: str) -> None:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM patient_records WHERE id = %s;", (record_id,))
                if cur.rowcount == 0:
                    raise ValueError("Expediente no encontrado")
                conn.commit()
        finally:
            conn.close()

    # Añadir diagnóstico/tratamiento (entry)
    @staticmethod
    def add_entry(record_id: str, payload: dict) -> dict:
        required = ["entry_date", "diagnosis", "treatment", "is_current"]
        for k in required:
            if payload.get(k) in (None, ""):
                raise ValueError(f"{k} es requerido")

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Validar record
                cur.execute("SELECT id FROM patient_records WHERE id = %s;", (record_id,))
                if not cur.fetchone():
                    raise ValueError("Expediente no encontrado")

                cur.execute("""
                    INSERT INTO record_entries
                      (record_id, entry_date, diagnosis, treatment, is_current)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *;
                """, (
                    record_id,
                    payload["entry_date"],  # YYYY-MM-DD
                    payload["diagnosis"].strip(),
                    payload["treatment"].strip(),
                    bool(payload["is_current"]),
                ))
                entry = cur.fetchone()
                conn.commit()
                return entry
        finally:
            conn.close()

    # Lista de diagnósticos/tratamientos del expediente (para la tabla)
    @staticmethod
    def list_entries(record_id: str) -> list[dict]:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM record_entries
                    WHERE record_id = %s
                    ORDER BY entry_date DESC, created_at DESC;
                """, (record_id,))
                return cur.fetchall()
        finally:
            conn.close()

    # Admin: obtener todos los expedientes
    @staticmethod
    def list_all_records() -> list[dict]:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        pr.*,
                        u.email AS user_email
                    FROM patient_records pr
                    LEFT JOIN users u ON u.id = pr.user_id
                    ORDER BY pr.created_at DESC;
                """)
                return cur.fetchall()
        finally:
            conn.close()

    # Paciente: traer su expediente vinculado al user_id
    @staticmethod
    def get_my_record(user_id: str) -> dict | None:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM patient_records
                    WHERE user_id = %s
                    LIMIT 1;
                """, (user_id,))
                record = cur.fetchone()
                return record
        finally:
            conn.close()

    @staticmethod
    def get_record_user_id(record_id: str) -> str | None:
        """Devuelve el user_id asociado al expediente (si está vinculado)."""
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT user_id FROM patient_records WHERE id = %s;", (record_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return str(row["user_id"]) if row.get("user_id") else None
        finally:
            conn.close()

    @staticmethod
    def update_entry(entry_id: str, data: dict) -> dict:
        allowed = {"entry_date", "diagnosis", "treatment", "is_current"}
        payload = {k: data.get(k) for k in allowed if k in data}

        if not payload:
            raise ValueError("No hay campos para actualizar.")

        sets = []
        values = []
        for k, v in payload.items():
            sets.append(f"{k} = %s")
            values.append(v)

        values.append(entry_id)

        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    UPDATE record_entries
                    SET {sets}
                    WHERE id = %s
                    RETURNING id, record_id, entry_date, diagnosis, treatment, is_current;
            """.format(sets=", ".join(sets)), tuple(values))
                row = cur.fetchone()
                if not row:
                    raise ValueError("Entry no encontrado.")

                conn.commit()
                return row
        finally:
            conn.close()
