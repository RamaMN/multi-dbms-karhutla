"""Dashboard Multi-DBMS: Karhutla Indonesia (data SIPONGI KEMENHUT).

  PostgreSQL  : provinsi + luas_karhutla (2018-2026)         -> data relasional
  MongoDB     : hotspot_detail (titik hotspot + GeoJSON)       -> data dokumen
        └──> pandas.merge(kode_wilayah) ──> Streamlit + Plotly
"""
import logging
import math
import os
import re
from datetime import timedelta, timezone

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient
from sqlalchemy import create_engine, text

from database.connections import build_pg_url, require_mongo_uri

log = logging.getLogger("karhutla")
st.set_page_config(page_title="Karhutla Indonesia · Multi-DBMS", page_icon="🔥", layout="wide")

MONGO_COLLECTION = "hotspot_detail"
WIB = timezone(timedelta(hours=7))
SUMBER = "SIPONGI KEMENHUT (sipongi.gakkum.kehutanan.go.id), diakses 12 November 2026"
WILAYAH_COLORS = {"Sumatera": "#4c9be8", "Jawa": "#59a14f", "Bali & Nusa Tenggara": "#edc948",
                  "Kalimantan": "#f28e2b", "Sulawesi": "#b07aa1", "Maluku": "#76b7b2", "Papua": "#e15759"}
CONF_ORDER = ["High", "Medium", "Low"]
CONF_COLORS = {"High": "#d62728", "Medium": "#ff9f1c", "Low": "#f2d600"}


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


# Loader SENGAJA melempar error (tidak ditelan) -> hasil gagal tidak ikut ter-cache.
@st.cache_data(ttl=600, show_spinner="Mengambil data dari PostgreSQL…")
def load_postgres():
    query = text("SELECT l.kode_wilayah, p.nama_provinsi AS provinsi, p.wilayah, l.tahun, l.luas_ha "
                 "FROM luas_karhutla l JOIN provinsi p ON p.kode_wilayah = l.kode_wilayah")
    with get_pg_engine().connect() as conn:
        df = pd.read_sql(query, conn)
    if df.empty:
        raise ValueError("Tabel luas_karhutla kosong. Jalankan database/seed_data.py")
    df["kode_wilayah"] = df["kode_wilayah"].astype(str).str.strip()
    df["tahun"] = df["tahun"].astype(int)
    df["luas_ha"] = df["luas_ha"].astype(float)
    return df


def normalise_hotspot(df):
    needed = ["kode_wilayah", "provinsi", "kab_kota", "kecamatan", "desa", "waktu", "satelit", "confidence", "lokasi"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Field MongoDB tidak lengkap: {missing}. Jalankan database/seed_data.py")
    df = df.copy()
    df["lon"] = df["lokasi"].apply(lambda g: float(g["coordinates"][0]))
    df["lat"] = df["lokasi"].apply(lambda g: float(g["coordinates"][1]))
    df["waktu"] = pd.to_datetime(df["waktu"], utc=True).dt.tz_convert(WIB)
    df["kode_wilayah"] = df["kode_wilayah"].astype(str).str.strip()
    return df[["kode_wilayah", "provinsi", "kab_kota", "kecamatan", "desa", "waktu", "satelit", "confidence", "lat", "lon"]]


@st.cache_data(ttl=600, show_spinner="Mengambil data dari MongoDB…")
def load_mongo():
    client = MongoClient(require_mongo_uri(secret), serverSelectionTimeoutMS=8000)
    try:
        docs = list(client[secret("MONGO_DB", "karhutla_db")][MONGO_COLLECTION].find({}, {"_id": 0}))
    finally:
        client.close()
    if not docs:
        raise ValueError("Koleksi hotspot_detail kosong. Jalankan database/seed_data.py")
    return normalise_hotspot(pd.DataFrame(docs))


def explain_error(e):
    """Pesan error yang aman ditampilkan: password/URI disensor."""
    if isinstance(e, (ValueError, RuntimeError)):
        return str(e)
    msg = f"{type(e).__name__}: {e}"
    for key in ("PG_PASS", "PG_URL", "MONGO_URI"):
        val = secret(key)
        if val:
            msg = msg.replace(val, "***")
    msg = re.sub(r"(://[^:/@\s]+:)[^@\s]+@", r"\1***@", msg)
    return msg[:400]


def try_load(loader):
    """Return (dataframe, None) jika sukses atau (None, pesan_error). Tidak ada data pengganti."""
    try:
        return loader(), None
    except Exception as e:
        log.exception("Gagal memuat sumber data")  # detail lengkap ada di log server (Manage app)
        return None, explain_error(e)


def plot(fig, height=None):
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=height)
    st.plotly_chart(fig, width="stretch")


def hbar(data, x, y, title, color=None, cmap=None, labels=None):
    fig = px.bar(data.sort_values(x), x=x, y=y, orientation="h", color=color, color_discrete_map=cmap,
                 labels=labels, text_auto=",.0f", title=title)
    fig.update_layout(yaxis_title=None, legend_title_text=None)
    plot(fig)


# ───────────────────────── 1. Muat data ─────────────────────────
df_luas, err_pg = try_load(load_postgres)
df_hot, err_mongo = try_load(load_mongo)

st.title("🔥 Karhutla Indonesia: Luas Terbakar & Sebaran Hotspot")
st.caption("🐘 PostgreSQL (luas karhutla per provinsi-tahun)  +  🍃 MongoDB (titik hotspot berkoordinat)  →  pandas merge  →  Plotly")

sb = st.sidebar
sb.header("🔌 Status Koneksi")
for icon, name, err, data in [("🐘", "PostgreSQL", err_pg, df_luas), ("🍃", "MongoDB", err_mongo, df_hot)]:
    if err is None:
        sb.success(f"{icon} {name}: terhubung ({len(data):,} data)")
    else:
        sb.error(f"{icon} {name}: gagal terhubung")
if sb.button("🔄 Muat ulang data"):
    st.cache_data.clear()
    st.rerun()

if err_pg or err_mongo:
    st.error("❌ Dashboard tidak dapat memuat data dari database.")
    for name, err in [("🐘 PostgreSQL", err_pg), ("🍃 MongoDB", err_mongo)]:
        if err:
            st.markdown(f"**{name}**")
            st.code(err, language=None)
    st.info(
        "**Periksa berurutan:**\n"
        "1. Secrets terisi (Streamlit Cloud → App → Settings → Secrets): `PG_URL` dan `MONGO_URI`.\n"
        "2. Database sudah di-seed: `python database/seed_data.py`.\n"
        "3. Supabase: pakai connection string **pooler** (koneksi langsung memakai IPv6).\n"
        "4. MongoDB Atlas → Network Access: izinkan akses dari Streamlit Cloud (mis. `0.0.0.0/0`).\n"
        "5. Klik **🔄 Muat ulang data** di sidebar.")
    st.stop()

meta = df_luas.drop_duplicates("kode_wilayah")[["kode_wilayah", "provinsi", "wilayah"]]
orphan_hot = sorted(set(df_hot["kode_wilayah"]) - set(meta["kode_wilayah"]))  # hotspot tanpa master provinsi

# ───────────────────────── 2. Filter ─────────────────────────
sb.header("🔍 Filter")
years = sorted(df_luas["tahun"].unique())
y_lo, y_hi = sb.slider("Rentang tahun (tren)", int(years[0]), int(years[-1]), (int(years[0]), int(years[-1])))
focus = sb.selectbox("Tahun fokus (peringkat & gabungan)", years[::-1])
wil_opts = sorted(meta["wilayah"].unique())
sel_wil = sb.multiselect("Wilayah", wil_opts, default=wil_opts)
prov_opts = sorted(meta.loc[meta["wilayah"].isin(sel_wil), "provinsi"])
sel_prov = sb.multiselect("Provinsi", prov_opts, default=prov_opts)
sel_sat = sb.multiselect("Satelit (hotspot)", sorted(df_hot["satelit"].unique()), default=sorted(df_hot["satelit"].unique()))
sel_conf = sb.multiselect("Confidence (hotspot)", CONF_ORDER, default=CONF_ORDER)

kode_sel = set(meta.loc[meta["provinsi"].isin(sel_prov), "kode_wilayah"])
luas_f = df_luas[df_luas["kode_wilayah"].isin(kode_sel)]
luas_range = luas_f[luas_f["tahun"].between(y_lo, y_hi)]
hot_f = df_hot[df_hot["kode_wilayah"].isin(kode_sel) & df_hot["satelit"].isin(sel_sat) & df_hot["confidence"].isin(sel_conf)]
if luas_f.empty:
    st.warning("Tidak ada provinsi yang dipilih. Longgarkan filter di sidebar.")
    st.stop()

# ───────────────────────── 3. Integrasi PostgreSQL × MongoDB ─────────────────────────
hot_prov = (hot_f.groupby("kode_wilayah", as_index=False)
            .agg(hotspot=("lat", "size"), hotspot_high=("confidence", lambda s: int((s == "High").sum()))))
luas_focus = luas_f[luas_f["tahun"] == focus][["kode_wilayah", "provinsi", "wilayah", "luas_ha"]]
base = (luas_focus.merge(hot_prov, on="kode_wilayah", how="left", validate="one_to_one")
        .fillna({"hotspot": 0, "hotspot_high": 0}).astype({"hotspot": int, "hotspot_high": int}))

# ───────────────────────── 4. KPI ─────────────────────────
tot_focus = float(luas_focus["luas_ha"].sum())
prev = float(luas_f.loc[luas_f["tahun"] == focus - 1, "luas_ha"].sum())
top_luas = luas_focus.loc[luas_focus["luas_ha"].idxmax()] if not luas_focus.empty else None
top_hot = base.loc[base["hotspot"].idxmax()] if base["hotspot"].max() > 0 else None

k = st.columns(5)
k[0].metric(f"🐘 Luas karhutla {focus}", f"{tot_focus:,.0f} ha",
            delta=f"{(tot_focus - prev) / prev * 100:+.0f}% vs {focus - 1}" if prev > 0 else None,
            delta_color="inverse", help="PostgreSQL · luas_karhutla")
k[1].metric(f"🐘 Provinsi terluas {focus}", top_luas["provinsi"] if top_luas is not None else "-",
            help=f"{top_luas['luas_ha']:,.0f} ha" if top_luas is not None else None)
k[2].metric("🍃 Titik hotspot", f"{len(hot_f):,}", help="MongoDB · hotspot_detail (snapshot)")
k[3].metric("🍃 Provinsi hotspot terbanyak", top_hot["provinsi"] if top_hot is not None else "-",
            help=f"{int(top_hot['hotspot'])} titik" if top_hot is not None else None)
k[4].metric("🍃 Confidence High", f"{int((hot_f['confidence'] == 'High').sum()):,}", help="MongoDB · hotspot_detail")

t0, t1 = df_hot["waktu"].min(), df_hot["waktu"].max()
st.info(f"Hotspot = snapshot {t0:%d-%m-%Y %H:%M} s.d. {t1:%d-%m-%Y %H:%M} WIB. "
        f"Luas karhutla {years[-1]} = data berjalan (belum satu tahun penuh).")

tab_map, tab_trend, tab_join, tab_data = st.tabs(
    ["🗺️ Peta Hotspot", "📈 Tren Luas Karhutla", "🔗 Gabungan PostgreSQL × MongoDB", "🗃️ Data & Arsitektur"])

# ───────────────────────── 5. Peta hotspot ─────────────────────────
with tab_map:
    mode = st.radio("Tampilan peta", ["Titik", "Kepadatan"], horizontal=True)
    if hot_f.empty:
        st.info("Tidak ada hotspot untuk kombinasi filter ini.")
    else:
        c_lat, c_lon = (hot_f["lat"].min() + hot_f["lat"].max()) / 2, (hot_f["lon"].min() + hot_f["lon"].max()) / 2
        span = max(float(np.ptp(hot_f["lon"])), float(np.ptp(hot_f["lat"])) * 1.6, 1.0)
        zoom = float(np.clip(math.log2(360 / span) + 0.1, 2.5, 7.0))
        col_map, col_bar = st.columns([2, 1])
        with col_map:
            view = hot_f.assign(waktu_wib=hot_f["waktu"].dt.strftime("%d-%m %H:%M"))
            common = dict(lat="lat", lon="lon", zoom=zoom, center={"lat": c_lat, "lon": c_lon},
                          map_style="open-street-map", height=600)
            if mode == "Titik":
                fig = px.scatter_map(view, color="confidence", color_discrete_map=CONF_COLORS,
                                     category_orders={"confidence": CONF_ORDER}, hover_name="provinsi",
                                     hover_data={"kab_kota": True, "kecamatan": True, "desa": True, "satelit": True,
                                                 "waktu_wib": True, "lat": False, "lon": False},
                                     labels={"confidence": "Confidence", "kab_kota": "Kab/Kota", "waktu_wib": "Waktu (WIB)"},
                                     opacity=0.85, **common)
                fig.update_traces(marker=dict(size=8))
            else:
                fig = px.density_map(view, radius=14, color_continuous_scale="YlOrRd", **common)
                fig.update_layout(coloraxis_colorbar_title="Kepadatan")
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, width="stretch")
        with col_bar:
            per_prov = hot_f.groupby("provinsi").size().rename("hotspot").reset_index()
            per_prov = per_prov.merge(meta[["provinsi", "wilayah"]], on="provinsi", how="left").nlargest(10, "hotspot")
            hbar(per_prov, "hotspot", "provinsi", "10 provinsi dengan hotspot terbanyak", "wilayah", WILAYAH_COLORS,
                 {"hotspot": "Titik", "wilayah": "Wilayah"})
        st.caption("Sumber titik: MongoDB `hotspot_detail`. Hotspot adalah indikasi anomali suhu dari satelit, "
                   "bukan kepastian adanya kebakaran.")

# ───────────────────────── 6. Tren luas karhutla ─────────────────────────
with tab_trend:
    if luas_range.empty:
        st.info("Tidak ada data pada rentang tahun ini.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            tot = luas_range.groupby("tahun", as_index=False)["luas_ha"].sum()
            fig = px.line(tot, x="tahun", y="luas_ha", markers=True, title="Total luas karhutla per tahun (ha)",
                          labels={"tahun": "Tahun", "luas_ha": "Hektare"})
            fig.update_xaxes(dtick=1)
            plot(fig)
        with c2:
            byw = luas_range.groupby(["tahun", "wilayah"], as_index=False)["luas_ha"].sum()
            fig = px.bar(byw, x="tahun", y="luas_ha", color="wilayah", color_discrete_map=WILAYAH_COLORS,
                         title="Luas karhutla per wilayah", labels={"tahun": "Tahun", "luas_ha": "Hektare", "wilayah": "Wilayah"})
            fig.update_xaxes(dtick=1)
            fig.update_layout(legend_title_text=None)
            plot(fig)
        c3, c4 = st.columns([1, 1])
        with c3:
            hbar(luas_focus.nlargest(10, "luas_ha"), "luas_ha", "provinsi", f"10 provinsi terluas, {focus} (ha)",
                 "wilayah", WILAYAH_COLORS, {"luas_ha": "Hektare", "wilayah": "Wilayah"})
        with c4:
            pivot = luas_range.pivot_table(index="provinsi", columns="tahun", values="luas_ha", aggfunc="sum")
            pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index].head(20)
            fig = go.Figure(go.Heatmap(
                z=np.log10(1 + pivot.values), x=[str(c) for c in pivot.columns], y=pivot.index, customdata=pivot.values,
                hovertemplate="%{y}<br>%{x}: %{customdata:,.0f} ha<extra></extra>", colorscale="YlOrRd",
                colorbar=dict(title="ha", tickvals=[0, 1, 2, 3, 4, 5], ticktext=["0", "10", "100", "1 rb", "10 rb", "100 rb"])))
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(title="Heatmap provinsi × tahun (skala log, 20 teratas)")
            plot(fig, height=480)
        st.caption("Sumber: PostgreSQL `luas_karhutla`. Tahun terakhir adalah data berjalan.")

# ───────────────────────── 7. Gabungan ─────────────────────────
with tab_join:
    st.markdown(f"**Luas karhutla {focus}** (🐘 PostgreSQL) digabung dengan **jumlah hotspot snapshot** (🍃 MongoDB) "
                "lewat `kode_wilayah`.")
    plot_df = base[(base["luas_ha"] > 0) & (base["hotspot"] > 0)]
    if len(plot_df) < 2:
        st.info("Data gabungan belum cukup untuk ditampilkan (butuh minimal 2 provinsi dengan luas dan hotspot > 0).")
    else:
        fig = px.scatter(plot_df, x="luas_ha", y="hotspot", color="wilayah", color_discrete_map=WILAYAH_COLORS,
                         text="provinsi", log_x=True, log_y=True, size_max=18,
                         labels={"luas_ha": f"Luas karhutla {focus} (ha, log)", "hotspot": "Titik hotspot snapshot (log)",
                                 "wilayah": "Wilayah"},
                         title=f"Luas karhutla {focus} vs hotspot saat ini")
        fig.update_traces(textposition="top center", marker=dict(size=11))
        plot(fig)
    if len(base) >= 5 and base["luas_ha"].nunique() > 1 and base["hotspot"].nunique() > 1:
        rho = base["luas_ha"].corr(base["hotspot"], method="spearman")
        st.caption(f"Korelasi peringkat Spearman ρ = **{rho:.2f}** (n = {len(base)} provinsi). "
                   "Hotspot adalah snapshot sekitar 24 jam, sedangkan luas adalah akumulasi tahunan, "
                   "jadi ini indikasi, bukan bukti sebab-akibat.")
    else:
        st.caption("Butuh minimal 5 provinsi bernilai bervariasi untuk menghitung korelasi.")
    show = base.sort_values("hotspot", ascending=False).rename(columns={
        "provinsi": "Provinsi", "wilayah": "Wilayah", "luas_ha": f"Luas {focus} (ha)", "hotspot": "Hotspot",
        "hotspot_high": "Hotspot High"}).drop(columns="kode_wilayah")
    st.dataframe(show, hide_index=True, width="stretch")

# ───────────────────────── 8. Data & arsitektur ─────────────────────────
with tab_data:
    if orphan_hot:
        st.warning(f"kode_wilayah pada hotspot tanpa master provinsi (tidak ikut join): {orphan_hot}")
    else:
        st.success(f"Integritas join OK: {df_hot['kode_wilayah'].nunique()} provinsi bertitik hotspot, semuanya ada di master "
                   f"PostgreSQL ({meta['kode_wilayah'].nunique()} provinsi).")
    st.markdown(
        "| DBMS | Engine | Fungsi | Isi |\n|---|---|---|---|\n"
        "| 1 | PostgreSQL | Data master & historis (skema ketat, relasi FK) | `provinsi`, `luas_karhutla` (provinsi × tahun) |\n"
        "| 2 | MongoDB Atlas | Data kejadian berlokasi (dokumen, GeoJSON) | `hotspot_detail`: titik, desa, satelit, confidence, waktu |\n\n"
        "Kunci integrasi: `kode_wilayah` → `pandas.merge(..., validate='one_to_one')`.")
    wide = (luas_f.pivot_table(index=["kode_wilayah", "provinsi", "wilayah"], columns="tahun", values="luas_ha", aggfunc="sum")
            .reset_index())
    wide.columns = [str(c) for c in wide.columns]
    st.subheader("Luas karhutla (ha) per provinsi dan tahun")
    st.dataframe(wide, hide_index=True, width="stretch")
    d1, d2 = st.columns(2)
    d1.download_button("📥 Unduh luas karhutla (CSV)", wide.to_csv(index=False).encode("utf-8"),
                       file_name="luas_karhutla_provinsi.csv", mime="text/csv")
    hot_out = hot_f.assign(waktu=hot_f["waktu"].dt.strftime("%Y-%m-%d %H:%M"))
    st.subheader(f"Titik hotspot ({len(hot_f):,} baris, sesuai filter)")
    st.dataframe(hot_out, hide_index=True, width="stretch", height=300)
    d2.download_button("📥 Unduh hotspot (CSV)", hot_out.to_csv(index=False).encode("utf-8"),
                       file_name="hotspot_detail.csv", mime="text/csv")
    st.caption(f"Sumber data: {SUMBER}. Detail sumber dan referensi kode: lihat README.md di repositori.")
