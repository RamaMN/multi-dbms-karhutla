"""Mengisi PostgreSQL (schema.sql + provinsi + luas_karhutla) dan MongoDB (koleksi hotspot_detail).

    python database/seed_data.py                  # seed kedua DBMS
    python database/seed_data.py --only postgres  # hanya PostgreSQL
    python database/seed_data.py --only mongo     # hanya MongoDB

Data diambil dari data/luas_karhutla_provinsi.csv dan data/hotspot_detail.csv (divalidasi dulu).
Kredensial dibaca dari environment variable atau .streamlit/secrets.toml (lihat README).
PostgreSQL di-upsert (aman diulang). Koleksi hotspot adalah snapshot: isinya diganti seluruhnya.
"""
import argparse
import os
from pathlib import Path

from pymongo import MongoClient
from sqlalchemy import create_engine, text

from connections import build_pg_url, require_mongo_uri
from data_loader import consistency_warnings, hotspot_docs, luas_rows, provinsi_rows

MONGO_COLLECTION = "hotspot_detail"

HERE = Path(__file__).resolve().parent
SECRETS_FILE = HERE.parent / ".streamlit" / "secrets.toml"

UPSERT_PROVINSI = text("""
INSERT INTO provinsi (kode_wilayah, nama_provinsi, wilayah)
VALUES (:kode_wilayah, :nama_provinsi, :wilayah)
ON CONFLICT (kode_wilayah) DO UPDATE SET nama_provinsi = EXCLUDED.nama_provinsi, wilayah = EXCLUDED.wilayah
""")
UPSERT_LUAS = text("""
INSERT INTO luas_karhutla (kode_wilayah, tahun, luas_ha)
VALUES (:kode_wilayah, :tahun, :luas_ha)
ON CONFLICT (kode_wilayah, tahun) DO UPDATE SET luas_ha = EXCLUDED.luas_ha
""")


def cfg(key, default=None):
    """Environment variable dulu, lalu .streamlit/secrets.toml (Python 3.11+)."""
    if os.getenv(key):
        return os.getenv(key)
    try:
        import tomllib
        if SECRETS_FILE.exists():
            value = tomllib.loads(SECRETS_FILE.read_text(encoding="utf-8")).get(key)
            if value is not None:
                return str(value)
    except Exception:
        pass
    return default


def seed_postgres():
    engine = create_engine(build_pg_url(cfg), connect_args={"connect_timeout": 15})
    ddl = (HERE / "schema.sql").read_text(encoding="utf-8")
    prov, luas = provinsi_rows(), luas_rows()
    with engine.begin() as conn:
        conn.exec_driver_sql(ddl)
        conn.execute(UPSERT_PROVINSI, prov)
        conn.execute(UPSERT_LUAS, luas)
    print(f"[PostgreSQL] provinsi: {len(prov)} baris, luas_karhutla: {len(luas)} baris di-upsert")


def seed_mongo():
    docs = hotspot_docs()
    client = MongoClient(require_mongo_uri(cfg), serverSelectionTimeoutMS=15000)
    try:
        col = client[cfg("MONGO_DB", "karhutla_db")][MONGO_COLLECTION]
        col.delete_many({})
        col.insert_many(docs)
        col.create_index([("lokasi", "2dsphere")])
        col.create_index("kode_wilayah")
        print(f"[MongoDB] {col.name}: {len(docs)} dokumen dimuat (snapshot diganti)")
    finally:
        client.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["postgres", "mongo"])
    args = ap.parse_args()
    for w in consistency_warnings():
        print("PERINGATAN:", w)
    if args.only in (None, "postgres"):
        seed_postgres()
    if args.only in (None, "mongo"):
        seed_mongo()


if __name__ == "__main__":
    main()
