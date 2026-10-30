"""Dashboard Multi-DBMS: Karhutla, ISPA & Asap Lintas Negara (Transboundary Haze).

  PostgreSQL (data_kesehatan)      ┐
                                   ├─> pandas.merge(prov_id) ─> filter ─> Streamlit + Plotly
  MongoDB Atlas (telemetri_sensor) ┘
"""
import logging
import math
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient
from sqlalchemy import create_engine, text

from database.connections import build_pg_url, require_mongo_uri
from database.reference_data import MONGO_COLS, mongo_docs, postgres_rows

log = logging.getLogger("karhutla")
st.set_page_config(page_title="Karhutla & Asap Lintas Negara", page_icon="🚨", layout="wide")

# Kategori ISPU (Permen LHK No. P.14/2020) -> verifikasi ulang di dokumen resmi sebelum dikutip
ISPU_LABELS = ["Baik", "Sedang", "Tidak Sehat", "Sangat Tidak Sehat", "Berbahaya"]
ISPU_BINS = [-math.inf, 50, 100, 200, 300, math.inf]
ISPU_COLORS = {"Baik": "#2ca02c", "Sedang": "#1f77b4", "Tidak Sehat": "#f2c200",
               "Sangat Tidak Sehat": "#ff7f0e", "Berbahaya": "#d62728"}
PULAU_COLORS = {"Sumatera": "#4c9be8", "Kalimantan": "#f28e2b", "Jawa": "#59a14f"}


# ───────────────────────── Konfigurasi & koneksi ─────────────────────────
def secret(key, default=None):
    """st.secrets (Streamlit Cloud / secrets.toml) -> environment variable -> default."""
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:  # secrets.toml tidak ada
        pass
    return os.getenv(key, default)


@st.cache_resource
def get_pg_engine():
    return create_engine(build_pg_url(secret), connect_args={"connect_timeout": 8}, pool_pre_ping=True)


def normalise_mongo(df):
    """Samakan skema dokumen MongoDB; error jelas jika field wajib tidak ada."""
    df = df.rename(columns={"ispu_pm25": "ispu"})  # kompatibel dengan skema lama
    missing = [c for c in MONGO_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Field MongoDB tidak lengkap: {missing}. Jalankan database/seed_data.py")

    def to_list(v):
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v if str(x).strip()]
        return [s.strip() for s in str(v).split(",") if s.strip()]

    df = df[MONGO_COLS].copy()
    df["negara_terdampak"] = df["negara_terdampak"].apply(to_list)
    for c in ["titik_hotspot", "ispu", "lahan_terbakar_ha", "lat", "lon"]:
        df[c] = pd.to_numeric(df[c], errors="raise")
    return df


# Fungsi loader SENGAJA melempar error (tidak ditelan) -> hasil gagal tidak ikut ter-cache.
@st.cache_data(ttl=600, show_spinner="Mengambil data dari PostgreSQL…")
def load_postgres():
    with get_pg_engine().connect() as conn:
        df = pd.read_sql(text("SELECT prov_id, nama_provinsi, pulau, total_ispa, korban_meninggal "
                              "FROM data_kesehatan"), conn)
    if df.empty:
        raise ValueError("Tabel data_kesehatan kosong. Jalankan database/seed_data.py")
    return df


@st.cache_data(ttl=600, show_spinner="Mengambil data dari MongoDB…")
def load_mongo():
    client = MongoClient(require_mongo_uri(secret), serverSelectionTimeoutMS=8000)
    try:
        col = client[secret("MONGO_DB", "karhutla_db")][secret("MONGO_COLLECTION", "telemetri_sensor")]
        docs = list(col.find({}, {"_id": 0}))
    finally:
        client.close()
    if not docs:
        raise ValueError("Koleksi telemetri_sensor kosong. Jalankan database/seed_data.py")
    return normalise_mongo(pd.DataFrame(docs))


def load_source(loader, demo_factory):
    """Return (dataframe, pesan_error). Jika gagal -> data demo + pesan error yang TAMPIL di UI."""
    try:
        return loader(), None
    except Exception as e:
        log.exception("Gagal memuat sumber data")  # detail lengkap hanya di log server
        safe = str(e) if isinstance(e, (ValueError, RuntimeError)) else type(e).__name__
        return demo_factory(), safe


def integrate(df_pg, df_mongo):
    """Federasi tingkat aplikasi: join one-to-one pada prov_id + laporan data yatim."""
    only_pg = sorted(set(df_pg["prov_id"]) - set(df_mongo["prov_id"]))
    only_mongo = sorted(set(df_mongo["prov_id"]) - set(df_pg["prov_id"]))
    joined = df_pg.merge(df_mongo, on="prov_id", how="inner", validate="one_to_one")
    joined["kategori_ispu"] = pd.cut(joined["ispu"], ISPU_BINS, labels=ISPU_LABELS).astype(str)
    joined["negara_str"] = joined["negara_terdampak"].apply(", ".join)
    return joined, only_pg, only_mongo


def plot(fig):
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, width="stretch")


def hbar(data, x, title, color, cmap, labels, hover=None):
    fig = px.bar(data.sort_values(x), x=x, y="nama_provinsi", orientation="h", color=color,
                 color_discrete_map=cmap, labels=labels, hover_data=hover, text_auto=",.0f", title=title)
    fig.update_layout(yaxis_title=None, legend_title_text=None)
    plot(fig)


# ───────────────────────── 1. Muat & integrasikan data ─────────────────────────
df_pg, err_pg = load_source(load_postgres, lambda: pd.DataFrame(postgres_rows()))
df_mongo, err_mongo = load_source(load_mongo, lambda: normalise_mongo(pd.DataFrame(mongo_docs())))

st.title("🚨 Multi-DBMS Data Pipeline: Karhutla, ISPA & Asap Lintas Negara")
st.caption("🐘 PostgreSQL (data kesehatan)  +  🍃 MongoDB Atlas (telemetri sensor & geospasial)  →  pandas merge  →  Plotly")

if err_pg or err_mongo:
    detail = "; ".join(f"{n}: {e}" for n, e in [("PostgreSQL", err_pg), ("MongoDB", err_mongo)] if e)
    st.warning(f"⚠️ **MODE DEMO** — data berikut bukan dari database langsung. {detail}")

try:
    df_all, only_pg, only_mongo = integrate(df_pg, df_mongo)
except Exception as e:
    st.error(f"Integrasi data gagal: {e}")
    st.stop()
if df_all.empty:
    st.error("Tidak ada prov_id yang cocok antara PostgreSQL dan MongoDB.")
    st.stop()

# ───────────────────────── 2. Sidebar ─────────────────────────
sb = st.sidebar
sb.header("🔌 Status Koneksi")
for icon, name, err, n in [("🐘", "PostgreSQL", err_pg, len(df_pg)), ("🍃", "MongoDB", err_mongo, len(df_mongo))]:
    (sb.success if err is None else sb.error)(
        f"{icon} {name}: terhubung ({n} data)" if err is None else f"{icon} {name}: gagal → data demo")
if sb.button("🔄 Muat ulang data"):
    st.cache_data.clear()
    st.rerun()

sb.header("🔍 Filter")
pulau_opts = sorted(df_all["pulau"].unique())
sel_pulau = sb.multiselect("Pulau", pulau_opts, default=pulau_opts)
prov_opts = sorted(df_all.loc[df_all["pulau"].isin(sel_pulau), "nama_provinsi"].unique())
sel_prov = sb.multiselect("Provinsi", prov_opts, default=prov_opts)
lo, hi = math.floor(df_all["ispu"].min()), math.ceil(df_all["ispu"].max())
hi = max(hi, lo + 1)
ispu_lo, ispu_hi = sb.slider("Rentang nilai ISPU", float(lo), float(hi), (float(lo), float(hi)), step=1.0)

df = df_all[df_all["pulau"].isin(sel_pulau) & df_all["nama_provinsi"].isin(sel_prov)
            & df_all["ispu"].between(ispu_lo, ispu_hi)].copy()
if df.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini. Longgarkan filter di sidebar.")
    st.stop()

# ───────────────────────── 3. Status peringatan ─────────────────────────
worst = df.loc[df["ispu"].idxmax()]
parah = df[df["ispu"] > 200]
tetangga = sorted({c for lst in parah["negara_terdampak"] for c in lst if c.lower() != "indonesia"})
pesan = (f"ISPU tertinggi **{worst['ispu']:.1f}** di **{worst['nama_provinsi']}** ({worst['kategori_ispu']}). "
         f"{len(parah)} dari {len(df)} provinsi berkategori Sangat Tidak Sehat atau lebih buruk. "
         f"Potensi asap lintas negara: **{', '.join(tetangga) if tetangga else 'tidak ada'}**.")
if worst["ispu"] > 300:
    st.error("🚨 " + pesan)
elif worst["ispu"] > 200:
    st.warning("⚠️ " + pesan)
else:
    st.success("✅ " + pesan)

# ───────────────────────── 4. KPI ─────────────────────────
k = st.columns(5)
k[0].metric("🐘 Total ISPA", f"{int(df['total_ispa'].sum()):,} jiwa", help="PostgreSQL · data_kesehatan")
k[1].metric("🐘 Meninggal", f"{int(df['korban_meninggal'].sum()):,} jiwa", help="PostgreSQL · data_kesehatan")
k[2].metric("🍃 Titik hotspot", f"{int(df['titik_hotspot'].sum()):,}", help="MongoDB · telemetri_sensor")
k[3].metric("🍃 ISPU tertinggi", f"{worst['ispu']:.1f}", help="MongoDB · telemetri_sensor")
k[4].metric("🍃 Lahan terbakar", f"{df['lahan_terbakar_ha'].sum():,.1f} ha", help="MongoDB · telemetri_sensor")

tab_map, tab_an, tab_data = st.tabs(["🗺️ Peta & Lintas Negara", "📊 Analisis", "🗃️ Data & Arsitektur"])

# ───────────────────────── 5. Peta ─────────────────────────
with tab_map:
    col_map, col_cty = st.columns([2, 1])
    with col_map:
        span = max(float(np.ptp(df["lat"])), float(np.ptp(df["lon"])), 1.0)
        zoom = float(np.clip(math.log2(360 / span) - 0.6, 3.0, 6.0))
        fig = px.scatter_map(
            df, lat="lat", lon="lon", size="titik_hotspot", size_max=38, color="kategori_ispu",
            color_discrete_map=ISPU_COLORS, category_orders={"kategori_ispu": ISPU_LABELS},
            hover_name="nama_provinsi",
            hover_data={"ispu": ":.1f", "titik_hotspot": True, "lahan_terbakar_ha": ":,.1f",
                        "korban_meninggal": True, "negara_str": True, "lat": False, "lon": False},
            labels={"kategori_ispu": "Kategori ISPU", "ispu": "ISPU", "titik_hotspot": "Hotspot",
                    "lahan_terbakar_ha": "Lahan terbakar (ha)", "korban_meninggal": "Meninggal",
                    "negara_str": "Negara terdampak"},
            center={"lat": float(df["lat"].mean()), "lon": float(df["lon"].mean())},
            zoom=zoom, map_style="open-street-map", height=560)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width="stretch")
        st.caption("Ukuran lingkaran = jumlah hotspot · warna = kategori ISPU provinsi.")
    with col_cty:
        ex = df.explode("negara_terdampak")
        ex = ex[ex["negara_terdampak"].str.lower() != "indonesia"]
        if ex.empty:
            st.info("Tidak ada negara tetangga terdampak pada filter ini.")
        else:
            cty = ex.groupby("negara_terdampak", as_index=False).agg(
                provinsi_sumber=("nama_provinsi", "nunique"), total_hotspot=("titik_hotspot", "sum"))
            fig = px.bar(cty.sort_values("total_hotspot"), x="total_hotspot", y="negara_terdampak",
                         orientation="h", text="provinsi_sumber", color_discrete_sequence=["#d62728"],
                         labels={"total_hotspot": "Total hotspot provinsi sumber", "negara_terdampak": ""},
                         title="Negara tetangga terdampak")
            fig.update_traces(texttemplate="%{text} provinsi")
            plot(fig)
            st.caption("Hotspot dijumlahkan dari provinsi yang asapnya tercatat mencapai negara tersebut.")

# ───────────────────────── 6. Analisis ─────────────────────────
with tab_an:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.scatter(df, x="ispu", y="korban_meninggal", size="total_ispa", color="pulau",
                         color_discrete_map=PULAU_COLORS, text="nama_provinsi", size_max=40,
                         labels={"ispu": "Nilai ISPU (MongoDB)", "korban_meninggal": "Meninggal (PostgreSQL)",
                                 "pulau": "Pulau", "total_ispa": "Total ISPA"},
                         title="ISPU vs korban meninggal (ukuran = total ISPA)")
        fig.update_traces(textposition="top center")
        if len(df) >= 3 and df["ispu"].nunique() > 1 and df["korban_meninggal"].nunique() > 1:
            slope, icpt = np.polyfit(df["ispu"], df["korban_meninggal"], 1)
            xs = np.array([df["ispu"].min(), df["ispu"].max()])
            fig.add_trace(go.Scatter(x=xs, y=slope * xs + icpt, mode="lines", name="Tren linear",
                                     line=dict(dash="dash", color="gray")))
            r = df["ispu"].corr(df["korban_meninggal"])
            plot(fig)
            st.caption(f"Pearson r = **{r:.2f}** (n = {len(df)} provinsi). Korelasi bukan bukti sebab-akibat; "
                       "angka absolut belum dinormalisasi per jumlah penduduk.")
            if len(df) < 5:
                st.warning("Sampel < 5 provinsi: koefisien korelasi tidak dapat diandalkan.")
        else:
            plot(fig)
            st.caption("Butuh minimal 3 provinsi dengan nilai bervariasi untuk menghitung korelasi.")
    with c2:
        hbar(df, "korban_meninggal", "Korban meninggal per provinsi", "pulau", PULAU_COLORS,
             {"korban_meninggal": "Jiwa", "pulau": "Pulau"})
    c3, c4 = st.columns(2)
    with c3:
        hbar(df, "titik_hotspot", "Titik hotspot per provinsi (warna = kategori ISPU)", "kategori_ispu",
             ISPU_COLORS, {"titik_hotspot": "Hotspot", "kategori_ispu": "Kategori ISPU"})
    with c4:
        hbar(df, "lahan_terbakar_ha", "Luas lahan terbakar (ha)", "pulau", PULAU_COLORS,
             {"lahan_terbakar_ha": "Hektare", "pulau": "Pulau"})

# ───────────────────────── 7. Data & arsitektur ─────────────────────────
with tab_data:
    if only_pg or only_mongo:
        st.warning(f"Data yatim (tidak ikut join): prov_id hanya di PostgreSQL = {only_pg or '-'}; "
                   f"hanya di MongoDB = {only_mongo or '-'}.")
    else:
        st.success(f"Integritas join OK: {len(df_all)} provinsi cocok 1:1 antara PostgreSQL dan MongoDB.")
    st.markdown(
        "| DBMS | Engine | Fungsi | Isi |\n|---|---|---|---|\n"
        "| 1 | PostgreSQL | Data master & kesehatan (skema ketat) | `data_kesehatan`: provinsi, pulau, ISPA, korban |\n"
        "| 2 | MongoDB Atlas | Telemetri sensor & geospasial (skema fleksibel) | `telemetri_sensor`: hotspot, ISPU, lahan, "
        "negara_terdampak (array), lat/lon |\n\n"
        "Kunci integrasi: `prov_id` → `pandas.merge(..., validate='one_to_one')`."
    )
    view = df.drop(columns=["negara_terdampak"]).rename(columns={"negara_str": "negara_terdampak"})
    st.dataframe(view, hide_index=True, width="stretch")
    st.download_button("📥 Unduh data gabungan (CSV)", view.to_csv(index=False).encode("utf-8"),
                       file_name="multi_dbms_karhutla.csv", mime="text/csv")
    st.caption("Sumber data, referensi kode, dan cara replikasi: lihat README.md di repositori.")
