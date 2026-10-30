"""Mengisi PostgreSQL (schema.sql + tabel data_kesehatan) dan MongoDB (koleksi telemetri_sensor).

    python database/seed_data.py                  # seed kedua DBMS
    python database/seed_data.py --only postgres  # hanya PostgreSQL
    python database/seed_data.py --only mongo     # hanya MongoDB
    python database/seed_data.py --export-json    # tulis ulang database/seed_mongodb.json

Kredensial dibaca dari environment variable atau .streamlit/secrets.toml (lihat README).
Skrip ini idempotent: aman dijalankan berulang kali (upsert berdasarkan prov_id).
"""
import argparse
import json
import os
from pathlib import Path

from pymongo import MongoClient, ReplaceOne
from sqlalchemy import create_engine, text

from connections import build_pg_url, require_mongo_uri
from reference_data import mongo_docs, postgres_rows

HERE = Path(__file__).resolve().parent
SECRETS_FILE = HERE.parent / ".streamlit" / "secrets.toml"

UPSERT_PG = text("""
INSERT INTO data_kesehatan (prov_id, nama_provinsi, pulau, total_ispa, korban_meninggal)
VALUES (:prov_id, :nama_provinsi, :pulau, :total_ispa, :korban_meninggal)
ON CONFLICT (prov_id) DO UPDATE SET
    nama_provinsi    = EXCLUDED.nama_provinsi,
    pulau            = EXCLUDED.pulau,
    total_ispa       = EXCLUDED.total_ispa,
    korban_meninggal = EXCLUDED.korban_meninggal
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
    rows = postgres_rows()
    with engine.begin() as conn:
        conn.exec_driver_sql(ddl)
        conn.execute(UPSERT_PG, rows)
    print(f"[PostgreSQL] data_kesehatan: {len(rows)} baris di-upsert")


def seed_mongo():
    client = MongoClient(require_mongo_uri(cfg), serverSelectionTimeoutMS=15000)
    try:
        col = client[cfg("MONGO_DB", "karhutla_db")][cfg("MONGO_COLLECTION", "telemetri_sensor")]
        col.create_index("prov_id", unique=True)
        docs = mongo_docs()
        col.bulk_write([ReplaceOne({"prov_id": d["prov_id"]}, d, upsert=True) for d in docs])
        print(f"[MongoDB] {col.name}: {len(docs)} dokumen di-upsert")
    finally:
        client.close()


def export_json():
    path = HERE / "seed_mongodb.json"
    path.write_text(json.dumps(mongo_docs(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Ditulis: {path}  (impor manual: mongoimport --jsonArray --collection telemetri_sensor --file {path.name})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["postgres", "mongo"])
    ap.add_argument("--export-json", action="store_true")
    args = ap.parse_args()
    if args.export_json:
        export_json()
        return
    if args.only in (None, "postgres"):
        seed_postgres()
    if args.only in (None, "mongo"):
        seed_mongo()


if __name__ == "__main__":
    main()
