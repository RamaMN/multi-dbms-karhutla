-- ============================================================
-- DBMS 1 : PostgreSQL (Supabase / Neon)
-- Fungsi : master provinsi + luas karhutla per provinsi per tahun (relasional)
-- Jalankan lewat SQL Editor, atau otomatis oleh database/seed_data.py
-- ============================================================
CREATE TABLE IF NOT EXISTS provinsi (
    kode_wilayah   CHAR(2)      PRIMARY KEY,
    nama_provinsi  VARCHAR(100) NOT NULL UNIQUE,
    wilayah        VARCHAR(50)  NOT NULL
);

CREATE TABLE IF NOT EXISTS luas_karhutla (
    kode_wilayah   CHAR(2)       NOT NULL REFERENCES provinsi (kode_wilayah),
    tahun          SMALLINT      NOT NULL CHECK (tahun BETWEEN 2000 AND 2100),
    luas_ha        NUMERIC(14,2) NOT NULL CHECK (luas_ha >= 0),
    PRIMARY KEY (kode_wilayah, tahun)
);

CREATE INDEX IF NOT EXISTS idx_luas_karhutla_tahun ON luas_karhutla (tahun);

-- ============================================================
-- DBMS 2 : MongoDB Atlas  (tidak memakai DDL)
-- Database : karhutla_db   Koleksi : hotspot_detail
-- Dokumen  : { kode_wilayah, provinsi, provinsi_asal, kab_kota, kecamatan, desa,
--              waktu (datetime), satelit, confidence,
--              lokasi: { type: "Point", coordinates: [lon, lat] } }
-- Indeks   : 2dsphere pada lokasi, indeks pada kode_wilayah (dibuat oleh seed_data.py)
-- Kunci integrasi antar-DBMS: kode_wilayah
-- ============================================================
