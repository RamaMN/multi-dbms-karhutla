"""Sumber tunggal data seed.

Dipakai oleh:
  - database/seed_data.py  -> mengisi PostgreSQL & MongoDB
  - app.py                 -> hanya untuk MODE DEMO (jika koneksi database gagal)

PENTING: ganti nilai di bawah dengan data asli dari sumber primer
(lihat README bagian "Sumber Data") sebelum dikumpulkan.
"""

PG_COLS = ["prov_id", "nama_provinsi", "pulau", "total_ispa", "korban_meninggal"]
MONGO_COLS = ["prov_id", "titik_hotspot", "ispu", "lahan_terbakar_ha", "negara_terdampak", "lat", "lon"]

DATA = [
    {"prov_id": 1, "nama_provinsi": "Riau", "pulau": "Sumatera", "total_ispa": 12500, "korban_meninggal": 12,
     "titik_hotspot": 185, "ispu": 280.5, "lahan_terbakar_ha": 3200.5,
     "negara_terdampak": ["Indonesia", "Singapura", "Malaysia"], "lat": 0.5104, "lon": 101.4383},
    {"prov_id": 2, "nama_provinsi": "Sumatera Selatan", "pulau": "Sumatera", "total_ispa": 15300, "korban_meninggal": 16,
     "titik_hotspot": 240, "ispu": 310.0, "lahan_terbakar_ha": 4100.2,
     "negara_terdampak": ["Indonesia", "Singapura"], "lat": -3.3199, "lon": 104.9147},
    {"prov_id": 3, "nama_provinsi": "Jambi", "pulau": "Sumatera", "total_ispa": 9800, "korban_meninggal": 8,
     "titik_hotspot": 95, "ispu": 160.8, "lahan_terbakar_ha": 1200.0,
     "negara_terdampak": ["Indonesia"], "lat": -1.6101, "lon": 103.6131},
    {"prov_id": 4, "nama_provinsi": "Kalimantan Tengah", "pulau": "Kalimantan", "total_ispa": 18400, "korban_meninggal": 24,
     "titik_hotspot": 290, "ispu": 340.2, "lahan_terbakar_ha": 4800.0,
     "negara_terdampak": ["Indonesia", "Malaysia", "Brunei Darussalam"], "lat": -1.6815, "lon": 113.3824},
    {"prov_id": 5, "nama_provinsi": "Kalimantan Barat", "pulau": "Kalimantan", "total_ispa": 14200, "korban_meninggal": 18,
     "titik_hotspot": 210, "ispu": 295.0, "lahan_terbakar_ha": 3900.2,
     "negara_terdampak": ["Indonesia", "Malaysia"], "lat": -0.0263, "lon": 109.3425},
    {"prov_id": 6, "nama_provinsi": "Kalimantan Timur", "pulau": "Kalimantan", "total_ispa": 11100, "korban_meninggal": 10,
     "titik_hotspot": 145, "ispu": 220.4, "lahan_terbakar_ha": 2100.5,
     "negara_terdampak": ["Indonesia", "Brunei Darussalam"], "lat": 0.5387, "lon": 116.4194},
    {"prov_id": 7, "nama_provinsi": "DKI Jakarta", "pulau": "Jawa", "total_ispa": 8500, "korban_meninggal": 3,
     "titik_hotspot": 12, "ispu": 85.0, "lahan_terbakar_ha": 50.0,
     "negara_terdampak": ["Indonesia"], "lat": -6.2088, "lon": 106.8456},
    {"prov_id": 8, "nama_provinsi": "Jawa Barat", "pulau": "Jawa", "total_ispa": 19200, "korban_meninggal": 7,
     "titik_hotspot": 45, "ispu": 120.5, "lahan_terbakar_ha": 350.0,
     "negara_terdampak": ["Indonesia"], "lat": -6.9175, "lon": 107.6191},
    {"prov_id": 9, "nama_provinsi": "Jawa Timur", "pulau": "Jawa", "total_ispa": 16800, "korban_meninggal": 5,
     "titik_hotspot": 30, "ispu": 105.0, "lahan_terbakar_ha": 210.0,
     "negara_terdampak": ["Indonesia"], "lat": -7.2504, "lon": 112.7688},
]


def postgres_rows():
    """Baris untuk tabel PostgreSQL `data_kesehatan`."""
    return [{k: d[k] for k in PG_COLS} for d in DATA]


def mongo_docs():
    """Dokumen untuk koleksi MongoDB `telemetri_sensor`."""
    return [{k: d[k] for k in MONGO_COLS} for d in DATA]
