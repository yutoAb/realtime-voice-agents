INSERT INTO hospitals(id, name, lat, lon) VALUES
    ('h_001', 'Waseda Clinic', 35.7081, 139.7209)
    ON CONFLICT (id) DO NOTHING;


INSERT INTO hospitals(id, name, lat, lon) VALUES
    ('h_002', 'Takadanobaba Hospital', 35.7123, 139.7031)
    ON CONFLICT (id) DO NOTHING;


-- それぞれの病院に本日以降の空き枠を生成（毎時 3 枠の例）
DO $$
DECLARE
base_ts TIMESTAMPTZ := date_trunc('hour', now());
h TEXT;
i INT;
BEGIN
FOR h IN SELECT id FROM hospitals LOOP
FOR i IN 0..8 LOOP
BEGIN
INSERT INTO slots(hospital_id, start_time)
VALUES (h, base_ts + make_interval(hours => i));
EXCEPTION WHEN unique_violation THEN
-- 既にあればスキップ
NULL;
END;
END LOOP;
END LOOP;
END$$;