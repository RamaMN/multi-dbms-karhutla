"""Membaca & memvalidasi CSV bersih di folder data/ untuk seed PostgreSQL dan MongoDB.

  data/luas_karhutla_provinsi.csv -> PostgreSQL: tabel provinsi + luas_karhutla
  data/hotspot_detail.csv         -> MongoDB: koleksi hotspot_detail (lokasi sebagai GeoJSON Point)

CSV dibuat dari berkas mentah SiPongi+ oleh database/prepare_data.py.
"""
import csv
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LUAS_FILE = DATA_DIR / "luas_karhutla_provinsi.csv"
HOTSPOT_FILE = DATA_DIR / "hotspot_detail.csv"

LUAS_COLS = ["kode_wilayah", "provinsi", "wilayah", "tahun", "luas_ha"]
HOTSPOT_COLS = ["kode_wilayah", "provinsi", "provinsi_asal", "kab_kota", "kecamatan", "desa", "waktu",
                "satelit", "confidence", "latitude", "longitude"]
CONFIDENCE = {"High", "Medium", "Low"}


def _read(path, cols):
    if not path.exists():
        raise FileNotFoundError(f"Berkas data tidak ditemukan: {path}. Jalankan database/prepare_data.py")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in cols if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: kolom wajib tidak ada: {missing}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name}: tidak ada baris data")
    return rows


def luas_rows():
    """Baris tervalidasi: (kode_wilayah, provinsi, wilayah, tahun, luas_ha)."""
    out, seen = [], set()
    for n, r in enumerate(_read(LUAS_FILE, LUAS_COLS), start=2):
        try:
            row = {"kode_wilayah": r["kode_wilayah"].strip().zfill(2), "provinsi": r["provinsi"].strip(),
                   "wilayah": r["wilayah"].strip(), "tahun": int(r["tahun"]), "luas_ha": float(r["luas_ha"])}
        except ValueError as e:
            raise ValueError(f"{LUAS_FILE.name} baris {n}: {e}") from None
        if row["luas_ha"] < 0 or not row["provinsi"]:
            raise ValueError(f"{LUAS_FILE.name} baris {n}: nilai tidak valid")
        key = (row["kode_wilayah"], row["tahun"])
        if key in seen:
            raise ValueError(f"{LUAS_FILE.name} baris {n}: duplikat {key}")
        seen.add(key)
        out.append(row)
    return out


def provinsi_rows():
    """Master provinsi unik, diturunkan dari data luas."""
    uniq = {}
    for r in luas_rows():
        prev = uniq.setdefault(r["kode_wilayah"], (r["provinsi"], r["wilayah"]))
        if prev != (r["provinsi"], r["wilayah"]):
            raise ValueError(f"Kode {r['kode_wilayah']} punya nama/wilayah berbeda: {prev} vs {(r['provinsi'], r['wilayah'])}")
    return [{"kode_wilayah": k, "nama_provinsi": v[0], "wilayah": v[1]} for k, v in sorted(uniq.items())]


def hotspot_docs():
    """Dokumen MongoDB tervalidasi. `waktu` -> datetime (zona waktu WIB), `lokasi` -> GeoJSON Point [lon, lat]."""
    out = []
    for n, r in enumerate(_read(HOTSPOT_FILE, HOTSPOT_COLS), start=2):
        try:
            lat, lon = float(r["latitude"]), float(r["longitude"])
            waktu = datetime.fromisoformat(r["waktu"])
        except ValueError as e:
            raise ValueError(f"{HOTSPOT_FILE.name} baris {n}: {e}") from None
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"{HOTSPOT_FILE.name} baris {n}: koordinat di luar rentang")
        if r["confidence"] not in CONFIDENCE:
            raise ValueError(f"{HOTSPOT_FILE.name} baris {n}: confidence '{r['confidence']}' tidak dikenal")
        out.append({"kode_wilayah": r["kode_wilayah"].strip().zfill(2), "provinsi": r["provinsi"].strip(),
                    "provinsi_asal": r["provinsi_asal"].strip(), "kab_kota": r["kab_kota"].strip(),
                    "kecamatan": r["kecamatan"].strip(), "desa": r["desa"].strip(), "waktu": waktu,
                    "satelit": r["satelit"].strip(), "confidence": r["confidence"],
                    "lokasi": {"type": "Point", "coordinates": [lon, lat]}})
    return out


def consistency_warnings():
    """Peringatan jika ada kode_wilayah pada hotspot yang tidak ada di master provinsi."""
    pg = {r["kode_wilayah"] for r in provinsi_rows()}
    orphan = sorted({d["kode_wilayah"] for d in hotspot_docs()} - pg)
    return [f"kode_wilayah pada hotspot tanpa master provinsi: {orphan}"] if orphan else []
