"""Pembangun URL koneksi PostgreSQL yang dipakai bersama oleh app.py dan seed_data.py.

Kredensial TIDAK ditulis di kode. Semuanya diambil lewat fungsi `get(key, default=None)`
(st.secrets / environment variable / .streamlit/secrets.toml).
"""
from sqlalchemy.engine import URL


def build_pg_url(get):
    url = get("PG_URL")
    if url:  # contoh: postgresql://user:pass@host:5432/postgres
        # Paksa driver psycopg2: SQLAlchemy terbaru memakai psycopg (v3) untuk skema "postgresql://".
        for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg2://" + url[len(prefix):]
        return url
    host = get("PG_HOST")
    if not host:
        raise RuntimeError("PG_URL atau PG_HOST belum diatur (lihat README bagian Konfigurasi).")
    return URL.create(
        "postgresql+psycopg2",
        username=get("PG_USER", "postgres"),
        password=get("PG_PASS"),
        host=host,
        port=int(get("PG_PORT", "5432")),
        database=get("PG_DB", "postgres"),
        query={"sslmode": get("PG_SSLMODE", "prefer")},
    )


def require_mongo_uri(get):
    uri = get("MONGO_URI")
    if not uri:
        raise RuntimeError("MONGO_URI belum diatur (lihat README bagian Konfigurasi).")
    return uri
