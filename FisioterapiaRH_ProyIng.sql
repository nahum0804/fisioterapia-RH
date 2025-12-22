-- =========================
-- Extensiones necesarias
-- =========================
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- =========================
-- Enum: estado de la cita
-- =========================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_status') THEN
    CREATE TYPE appointment_status AS ENUM (
      'requested',
      'confirmed',
      'rejected',
      'cancelled',
      'completed'
    );
  END IF;
END $$;

-- =========================
-- Pacientes
-- =========================
CREATE TABLE IF NOT EXISTS patients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  owner_user_id BIGINT,
  full_name TEXT NOT NULL,
  relation_to_booker TEXT,
  birth_date DATE,
  notes TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_patients_owner_user_id
  ON patients(owner_user_id);

-- =========================
-- Citas
-- =========================
CREATE TABLE IF NOT EXISTS appointments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  booked_by_user_id BIGINT NOT NULL,
  patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

  description TEXT NOT NULL,
  comment TEXT,
  considerations TEXT,

  requested_start TIMESTAMPTZ,
  requested_end   TIMESTAMPTZ,

  scheduled_start TIMESTAMPTZ,
  scheduled_end   TIMESTAMPTZ,

  status appointment_status NOT NULL DEFAULT 'requested',

  is_paid BOOLEAN NOT NULL DEFAULT FALSE,
  paid_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT chk_paid_at
    CHECK (
      (is_paid = FALSE AND paid_at IS NULL)
      OR
      (is_paid = TRUE AND paid_at IS NOT NULL)
    ),

  CONSTRAINT chk_requested_range
    CHECK (
      requested_start IS NULL OR requested_end IS NULL
      OR requested_end > requested_start
    ),

  CONSTRAINT chk_scheduled_range
    CHECK (
      scheduled_start IS NULL OR scheduled_end IS NULL
      OR scheduled_end > scheduled_start
    )
);

CREATE INDEX IF NOT EXISTS idx_appointments_booked_by
  ON appointments(booked_by_user_id);

CREATE INDEX IF NOT EXISTS idx_appointments_patient
  ON appointments(patient_id);

CREATE INDEX IF NOT EXISTS idx_appointments_status
  ON appointments(status);

CREATE INDEX IF NOT EXISTS idx_appointments_scheduled_start
  ON appointments(scheduled_start);

ALTER TABLE appointments
  DROP CONSTRAINT IF EXISTS appointments_no_overlap;

ALTER TABLE appointments
  ADD CONSTRAINT appointments_no_overlap
  EXCLUDE USING gist (
    tstzrange(scheduled_start, scheduled_end, '[)') WITH &&
  )
  WHERE (
    scheduled_start IS NOT NULL
    AND scheduled_end IS NOT NULL
    AND status IN ('confirmed', 'completed')
  );

-- =========================
-- Agenda semanal base
-- =========================
CREATE TABLE IF NOT EXISTS therapist_weekly_availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
  start_time TIME NOT NULL,
  end_time   TIME NOT NULL CHECK (end_time > start_time),

  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_weekly_availability_day
  ON therapist_weekly_availability(day_of_week);

ALTER TABLE therapist_weekly_availability
  DROP CONSTRAINT IF EXISTS weekly_availability_no_overlap;

ALTER TABLE therapist_weekly_availability
  ADD CONSTRAINT weekly_availability_no_overlap
  EXCLUDE USING gist (
    day_of_week WITH =,
    tsrange(
      ('2000-01-01'::date + start_time)::timestamp,
      ('2000-01-01'::date + end_time)::timestamp,
      '[)'
    ) WITH &&
  )
  WHERE (is_active = TRUE);

-- =========================
-- Bloqueos (no disponibilidad)
-- =========================
CREATE TABLE IF NOT EXISTS therapist_time_off (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  start_at TIMESTAMPTZ NOT NULL,
  end_at   TIMESTAMPTZ NOT NULL CHECK (end_at > start_at),

  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_time_off_start
  ON therapist_time_off(start_at);

ALTER TABLE therapist_time_off
  DROP CONSTRAINT IF EXISTS time_off_no_overlap;

ALTER TABLE therapist_time_off
  ADD CONSTRAINT time_off_no_overlap
  EXCLUDE USING gist (
    tstzrange(start_at, end_at, '[)') WITH &&
  );

-- =========================
-- Historial / auditoría
-- =========================
CREATE TABLE IF NOT EXISTS appointment_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  appointment_id UUID NOT NULL
    REFERENCES appointments(id) ON DELETE CASCADE,

  event_type TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  note TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_appointment_events_appointment
  ON appointment_events(appointment_id);

-- =========================
-- Trigger updated_at
-- =========================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_appointments_updated_at ON appointments;

CREATE TRIGGER trg_appointments_updated_at
BEFORE UPDATE ON appointments
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS site_info (
  id SMALLINT PRIMARY KEY DEFAULT 1,

  info TEXT NOT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT site_info_single_row CHECK (id = 1)
);

DROP TRIGGER IF EXISTS trg_site_info_updated_at ON site_info;

CREATE TRIGGER trg_site_info_updated_at
BEFORE UPDATE ON site_info
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

INSERT INTO site_info (id, info)
VALUES (
  1,
  'Bienvenidos! Fisioterapia RH ofrece el mejor servicio de la zona, con precio y horarios accesibles para ayudarte con tu rehabilitacion, contracturas y demas'
)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS site_location (
  id SMALLINT PRIMARY KEY DEFAULT 1,

  location TEXT NOT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT site_location_single_row CHECK (id = 1)
);

DROP TRIGGER IF EXISTS trg_site_location_updated_at ON site_location;

CREATE TRIGGER trg_site_location_updated_at
BEFORE UPDATE ON site_location
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

INSERT INTO site_location (id, location)
VALUES (
  1,
  'Hogar de Ancianos San Vicente de Paul, Ciudad Quesada, San Carlos, Costa Rica'
)
ON CONFLICT (id) DO NOTHING;

-- 1) Extensión para generar UUID en Postgres
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2) Borrar tabla si existe (solo si estás reiniciando)
DROP TABLE IF EXISTS users;

-- 3) Crear tabla users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT users_role_check CHECK (role IN ('admin','user'))
);

-- 4) Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

SELECT * FROM users;
