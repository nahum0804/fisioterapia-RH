from psycopg2.extras import RealDictCursor
from app.db import get_connection

class SiteService:

    @staticmethod
    def get_info():
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT info FROM site_info LIMIT 1;")
                return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def update_info(text: str):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE site_info
                    SET info = %s, updated_at = now()
                    WHERE id = 1;
                """, (text,))
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_location():
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT location FROM site_location LIMIT 1;")
                return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def update_location(text: str):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE site_location
                    SET location = %s, updated_at = now()
                    WHERE id = 1;
                """, (text,))
                conn.commit()
        finally:
            conn.close()
