from datetime import datetime
from ..extensions import db
from ..models import PlannerItem, Appointment

class PlannerSync:
    @staticmethod
    def upsert_for_appointment(appt: Appointment):
        # Solo si hay scheduled_start/end (lo que se muestra en agenda)
        if not appt.scheduled_start or not appt.scheduled_end:
            item = PlannerItem.query.filter_by(appointment_id=appt.id).first()
            if item:
                db.session.delete(item)
            return None

        # ✅ title SIEMPRE válido (nunca vacío)
        # - Si tiene usuario: "Cita: Nombre"
        # - Si no: usa descripción o "Cita manual"
        patient_name = None
        try:
            # por si tienes relación appt.user cargada
            patient_name = getattr(appt.user, "full_name", None)
        except Exception:
            patient_name = None

        title = (
            f"Cita: {patient_name}"
            if patient_name
            else (appt.description.strip() if appt.description and appt.description.strip() else "Cita manual")
        )

        # ✅ note: usa comment si existe (o None)
        note = appt.comment.strip() if appt.comment and appt.comment.strip() else None

        item = PlannerItem.query.filter_by(appointment_id=appt.id).first()

        if not item:
            item = PlannerItem(
                kind="manual_appointment",          # ✅ coincide con tu ENUM
                title=title,                         # ✅ no vacío
                note=note,
                start_at=appt.scheduled_start,
                end_at=appt.scheduled_end,
                all_day=False,
                appointment_id=appt.id,
            )
            db.session.add(item)
        else:
            item.kind = "manual_appointment"
            item.title = title                      # ✅ actualiza
            item.note = note                        # ✅ actualiza
            item.start_at = appt.scheduled_start
            item.end_at = appt.scheduled_end
            item.all_day = False

        item.updated_at = datetime.utcnow()
        return item
