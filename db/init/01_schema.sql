CREATE TABLE IF NOT EXISTS hospitals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
);


CREATE TABLE IF NOT EXISTS slots (
    id BIGSERIAL PRIMARY KEY,
    hospital_id TEXT NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    reserved BOOLEAN NOT NULL DEFAULT FALSE,
    reserved_at TIMESTAMPTZ,
    visit_id BIGINT,
    UNIQUE (hospital_id, start_time)
);


CREATE TABLE IF NOT EXISTS visits (
    id BIGSERIAL PRIMARY KEY,
    hospital_id TEXT NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    slot_id BIGINT NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
    name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- 予約一意性（1スロット = 1予約）
CREATE UNIQUE INDEX IF NOT EXISTS idx_slots_unique_visit ON slots(visit_id) WHERE visit_id IS NOT NULL;