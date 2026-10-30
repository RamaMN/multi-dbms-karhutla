-- ============================================================
-- DBMS 1 : PostgreSQL (Supabase / Neon)
-- Fungsi : data master wilayah + data kesehatan (ISPA)
-- Jalankan lewat SQL Editor, atau otomatis oleh database/seed_data.py
-- ============================================================
CREATE TABLE IF NOT EXISTS data_kesehatan (
    prov_id           INTEGER      PRIMARY KEY,
    nama_provinsi     VARCHAR(100) NOT NULL UNIQUE,
    pulau             VARCHAR(50)  NOT NULL,
    total_ispa        INTEGER      NOT NULL CHECK (total_ispa >= 0),
    korban_meninggal  INTEGER      NOT NULL CHECK (korban_meninggal >= 0),
    CHECK (korban_meninggal <= total_ispa)
);

CREATE INDEX IF NOT EXISTS idx_data_kesehatan_pulau ON data_kesehatan (pulau);

-- ============================================================
-- DBMS 2 : MongoDB Atlas  (tidak memakai DDL)
-- Database  : karhutla_db
-- Koleksi   : telemetri_sensor  (unique index pada prov_id, dibuat oleh seed_data.py)
-- Dokumen   : { prov_id, titik_hotspot, ispu, lahan_terbakar_ha,
--               negara_terdampak: [..], lat, lon }
-- Kunci integrasi antar-DBMS: prov_id
-- ============================================================
